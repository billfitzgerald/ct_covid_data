from pprint import pprint
import json
import requests 
import pandas as pd
import os
import datetime as dt
from datetime import datetime
from configparser import ConfigParser
import base64

path_to_batches = "batches/"
batch_files = ['ct_river_area.json', 'ledgelight.json', 'lyme_oldlyme.json']
add_style = "yes"
export_html = "yes"
export_update = "yes"
create_blog = "yes"

## External sources
opening = "source/opening.txt"
data_intro = "source/data_intro.txt"
style_declaration = "source/style.txt"
creds = "creds/creds_batch.ini"
population = "source/ct_population.csv"

### Case-specific information
case_initial = 14 # number of most recent reports to show
# interval is measured in number of reports. In general, 5 reports come out 
# every 7 days, so to go back 28 days enter 20
case_interval = [10, 20, 64, 128]
### Vax specific information
vax_initial = 3 # number of most recent vax level reports to show

# set ouput directories
report_dir = 'report/'

###########################################
# Use care if adjusting values below here #
###########################################

dir_list = [report_dir]
for d in dir_list:
	try:
		os.makedirs(d)
	except FileExistsError:
		pass

#Read creds.ini file
config = ConfigParser()
config.read(creds)
#Get options for details to include in summaries, and file format export options
creds = config["WORDPRESS"]
url_page = creds["url_page"]
url_post = creds["url_post"]
user = creds["username"]
password = creds["password"]

df_vax = pd.DataFrame(columns=['town', 'reported_date', 'age_group', 'initiated', 'vaccinated', 'change'])
df_vax_tmp = pd.DataFrame(columns=['town', 'reported_date', 'age_group', 'initiated', 'vaccinated', 'change'])
df_cases = pd.DataFrame(columns=['town', 'date', 'total_cases', 'case_change', 'total_deaths', 'death_change'])
df_ca_tmp = pd.DataFrame(columns=['town', 'date', 'total_cases', 'case_change', 'total_deaths', 'death_change'])
df_report = pd.DataFrame(columns=['town', 'text', 'sequence'])
df_fips = pd.DataFrame(columns=['county_name', 'fips_code', 'report_date', 'seven_day', 'positivity','level'])
df_fips_tmp = pd.DataFrame(columns=['county_name', 'fips_code', 'report_date', 'seven_day', 'positivity','level'])
df_hospital = pd.DataFrame(columns=['county_name', 'date_updated', 'hosp_cases', 'new_hosp'])
df_hosp = pd.DataFrame(columns=['county_name', 'date_updated', 'hosp_cases', 'new_hosp'])

## Functions      ##
## Clean up dates ##
def human_date(dirty_date):
	if len(str(dirty_date)) > 10:
		dirty_date = dirty_date[:10]
	else:
		pass
	try:
		clean_date = datetime.strptime(dirty_date, '%Y-%m-%d')
		clean_date = clean_date.strftime("%b %d, %Y")
	except:
		clean_date = "Nonstandard date format"
	return clean_date

## Clean up timedeltas ##
def clean_timedelta(td):
	# this is brittle; it assumes 00:00:00
	td_list = str(td).split(" 00:")
	clean_td = td_list[0]
	if clean_td == "1 days":
		clean_td = "24 hours"
	else:
		pass
	return clean_td

## Handle language around numbers ##
def pluralizer(number, context):
	if context == "town_cases":
		inc_desc = "more"
		low_desc = "counts have been adjusted to correct past data by"
	elif context == "hospital":
		inc_desc = "additional"
		low_desc = "less"

	if number > 0:
		if number == 1:
			pl_text = f'<b class="red">{number} {inc_desc} person</b> was'
		else:
			pl_text = f'<b class="red">{number} {inc_desc} people</b> were'
	elif number == 0:
		pl_text = f'there has been <b>no change</b> in the number of people'
	elif number < 0:
		not_neg = int(number) * -1
		if not_neg == 1:
			pl_text = f'<b class="blue">{not_neg} {low_desc} person</b> is'
		else:
			pl_text = f'<b class="blue">{not_neg} {low_desc} people</b> were'
		
	else:
		pl_text = "check the numbers"

	return pl_text
		

#date/time info
rightnow = dt.datetime.today()
starttime = rightnow + dt.timedelta(days=1)
week_away = rightnow + dt.timedelta(days=-7)
forty_five = rightnow + dt.timedelta(days=-45)
sy = starttime.strftime("%Y")
sm = starttime.strftime("%m")
sd = starttime.strftime("%d")
current = f"{sy}-{sm}-{sd}T00:00:00"

way = week_away.strftime("%Y")
wam = week_away.strftime("%m")
wad = week_away.strftime("%d")
week_prior = f"{way}-{wam}-{wad}T00:00:00"

ffay = forty_five.strftime("%Y")
ffam = forty_five.strftime("%m")
ffad = forty_five.strftime("%d")
forty_five_prior = f"{ffay}-{ffam}-{ffad}T00:00:00"

year = rightnow.strftime("%Y")
month = rightnow.strftime("%m")
day = rightnow.strftime("%d")
hour = rightnow.strftime("%H")
minute = rightnow.strftime("%M")

scan_datetime = f"{year}_{month}_{day}_{hour}_{minute}"
nowoclock = rightnow.strftime("%b %d, %Y")

run_time = f"This report was generated on {nowoclock} at {hour}:{minute}. "

# vax date values - generally no need to adjust this unless you want a longer time interval
startdate = forty_five_prior
enddate = current

#case values - generally no need to adjust this unless you want a longer time interval
startcase = forty_five_prior
endcase = current


# Get population numbers for towns
with open(population) as input:
	df_population = pd.read_csv(input)

towns_for_query = []
fips_for_query = []
print(f"Preparing to import data.\n")
for bf in batch_files:
	fn = path_to_batches + bf
	with open(fn) as input:
		data = json.load(input)
		town_list = data['town_list']
		for t in town_list:
			if t not in towns_for_query:
				towns_for_query.append(t)
			else:
				pass
		fips_code = data['fips_code']
		for f in fips_code:
			if f not in fips_for_query:
				fips_for_query.append(f)
			else:
				pass
for t in towns_for_query:
	df_ca_tmp = df_ca_tmp[0:0]
	print(f"   - Getting case and death rate data for {t}")
	case_url = f"https://data.ct.gov/resource/28fr-iqnx.json?town={t}&$where=lastupdatedate between '{startcase}' and '{endcase}'"
	case_data = json.loads(requests.get(case_url).text)
	past_case = 0
	past_death = 0
	for c in case_data:
		town = c['town']
		date = c['lastupdatedate'][:10]
		total_cases = int(c['towntotalcases'])
		case_change = 0
		total_deaths = int(c['towntotaldeaths'])
		death_change = 0
		case_obj = pd.Series([town, date, total_cases, case_change, total_deaths, death_change], index=df_ca_tmp.columns)
		df_ca_tmp = df_ca_tmp.append(case_obj, ignore_index=True)
	case_difference = df_ca_tmp['total_cases'].diff()
	death_difference = df_ca_tmp['total_deaths'].diff()
	df_ca_tmp['case_change'] = case_difference
	df_ca_tmp['death_change'] = death_difference
	df_cases = df_cases.append(df_ca_tmp)
## Moving on to vax rates by town
	df_vax_tmp = df_vax_tmp[0:0]
	print(f"   * Getting vaccination rate data for {t}\n")
	vax_url = f"https://data.ct.gov/resource/gngw-ukpw.json?town={t}&$where=dateupdated%20between%20'{startdate}'%20and%20'{enddate}'"
	vax_data = json.loads(requests.get(vax_url).text)
	for v in vax_data:
		town = v['town']
		reported_date = v['dateupdated'][:10]
		age_group = v['age_group']
		initiated = v['initiated_vaccination_percent']
		vaccinated = v['fully_vaccinated_percent']
		change = 0
		vax_obj = pd.Series([town, reported_date, age_group, initiated, vaccinated, change], index=df_vax.columns)
		df_vax = df_vax.append(vax_obj, ignore_index=True)
	#TODO get diff on change by age group

county_name_list = []
county_fips_dict = {}
for f in fips_for_query:
	print(f" ** Getting county-level transmission data from the CDC for {f}\n")
	fips_url = f"https://data.cdc.gov/resource/8396-v7yb.json?fips_code={f}&$where=report_date%20between%20'{forty_five_prior}'%20and%20'{current}'"
	fips_data = json.loads(requests.get(fips_url).text)
	for fd in fips_data:
		county_name = fd['county_name']
		if county_name not in county_name_list:
			county_name_list.append(county_name)
			cn = county_name.replace(" County", "")
			hold = {f:cn}
			county_fips_dict.update(hold) 
		report_date = fd['report_date'][:10]
		seven_day = fd['cases_per_100k_7_day_count']
		try:
			positivity = fd['percent_test_results_reported']
		except:
			positivity = "not reported"
		level = fd['community_transmission_level']
		fips_obj = pd.Series([county_name, f, report_date, seven_day, positivity, level], index=df_fips.columns)
		df_fips = df_fips.append(fips_obj, ignore_index=True)

for c in county_name_list:
	print(f" ** Getting county-level hospitalization data for {c}\n")
	cnl_call = c.replace(" County", "")
	hosp_url = f"https://data.ct.gov/resource/bfnu-rgqt.json?county={cnl_call}&$where=dateupdated%20between%20'{forty_five_prior}'%20and%20'{current}'"
	hospital_data = json.loads(requests.get(hosp_url).text)
	df_hosp = df_hosp[0:0]
	for hd in hospital_data:
		county_name = c
		date_updated = hd['dateupdated'][:10]
		hosp_cases = int(hd['hospitalization'])
		new_hosp = 0
		hosp_list = []
		hosp_obj = pd.Series([county_name, date_updated, hosp_cases, new_hosp], index=df_hosp.columns)
		df_hosp = df_hosp.append(hosp_obj, ignore_index=True)
	difference = df_hosp['hosp_cases'].diff()
	df_hosp['new_hosp'] = difference
	df_hospital = df_hospital.append(df_hosp)

df_cases['date'] = pd.to_datetime(df_cases['date'])
df_vax['reported_date'] = pd.to_datetime(df_vax['reported_date'])
df_fips['report_date'] = pd.to_datetime(df_fips['report_date'])
df_hospital['date_updated'] = pd.to_datetime(df_hospital['date_updated'])

for bf in batch_files:
	fn = path_to_batches + bf
	with open(fn) as input:
		report_opening = ""
		blog_post = ""
		full_report = ""
		counties_report = []
		print(f"Preparing report; processing {bf}\n")
		data = json.load(input)
		alltowns = data['batch_name']
		batch_desc = data['batch_desc']
		if len(batch_desc) > 2:
			batch_desc = f"<p>{batch_desc}</p>"
		else:
			batch_desc = ""
		run_schools = data['run_schools']
		ifschools = data['ifschools']
		school_intro = data['school_intro']
		school_cases = data['school_cases']
		pageID = data['pageID']
		category = data['categoryID']
		post_author = data['post_author']
		output_file = data['output']
		detailed_report_url = data['detailed_report_url']
## Set initial reporting language
#		title = f"Covid19 Vaccination Levels and Positive Cases in {alltowns}" # Report Title
#		blog_title = f"Daily Summary for {alltowns}" # Blog post title
		with open(data_intro) as di:
			intro_text = di.read()
		report_intro = intro_text + "<p>" + run_time + "</p>" + "<h2>1. Overview</h2>" + batch_desc 
		# Set link to named anchors
		anchor_links = "<h3>Jump to detailed reports:</h3><ul>"
		town_list = data['town_list']
		for t in town_list:
			named_anchor = ''.join(t.split()).lower()
			named_anchor_vax = f'"#{named_anchor}-vaccination"'
			named_anchor_cases = f'"#{named_anchor}-cases"'
			nat = f'"#{named_anchor}"'
			links = f'<li><a href={nat}>{t}</a></li>'
			anchor_links = anchor_links + links
		if run_schools == "yes":
			anchor_links = anchor_links + f'</ul><a href="#schools">Positive cases in schools.</a>'
		else:
			anchor_links = anchor_links + "</ul>"
		fips_code = data['fips_code']
		for f in fips_code:
			for key,value in county_fips_dict.items():
				if key == f:
					counties_report.append(value)
				else:
					pass
		case_change_all = 0
		week_change_all = 0
		week_death_change = 0
		month_change_all = 0
		month_death_change = 0
		town_case_full = ""
		town_case_summary = ""
		town_count = 0
		total_population = 0
		for t in town_list:
			# Get population for the town
			df_pop_filter = df_population[(df_population['town'] == t)]
			town_pop = df_pop_filter['pop'].iloc[0]
			tp = int(town_pop)
			total_population = total_population + tp
			tp = "{:,}".format(tp)
			pop_blurb = f"<p>{tp} people live in {t}.</p>"
			# Create town headings for summary and full reports
			town_count += 1
			tc = town_count + 1
			named_anchor_town = ''.join(t.split()).lower()
			named_anchor_town = f'id="{named_anchor_town}"'
			opening_title = "<h3>1." + str(town_count) + ". " + t + "</h3>" + pop_blurb
			town_title = "<hr><h2 " + named_anchor_town + ">" + str(tc) + ". " + t + "</h2>" + pop_blurb
			pop_blurb = f"<p>{tp} people live in {t}.</p>"
			######################
			## Get Case Numbers ##
			######################
			df_case_town_filter = df_cases[df_cases['town'] == t]
			df_case_town_filter.sort_values(by=['date'], inplace=True, ascending=False)
			# current count
			case_current_date = df_case_town_filter['date'].iloc[0]
			case_one_prior_date = df_case_town_filter['date'].iloc[1]
			time_between_reports = case_current_date - case_one_prior_date
			tbr = clean_timedelta(time_between_reports)
			ccd = human_date(str(case_current_date)[:10])
			current_change = df_case_town_filter['case_change'].iloc[0]
			c_change = pluralizer(current_change, "town_cases")
			case_change_all = case_change_all + int(current_change)
			current_total = df_case_town_filter['total_cases'].iloc[0]
			yesterday_total = df_case_town_filter['total_cases'].iloc[1]
			current_death = df_case_town_filter['total_deaths'].iloc[0]
			town_case = f"<ul><li>As of {ccd}: {c_change} positive for Covid over the last <b>{tbr}</b> (from {yesterday_total} people to {current_total} people).</li>"
			town_case_full = town_case_full + town_title + town_case
			town_case_summary = town_case_summary + opening_title + town_case

			# seven day count
			case_week_date = df_case_town_filter['date'].iloc[5]
			cwd = human_date(str(case_week_date)[:10])
			week_day_lapse = case_current_date - case_week_date
			wdl = clean_timedelta(week_day_lapse)
			week_total = df_case_town_filter['total_cases'].iloc[5]
			week_change = int(current_total) - int(week_total)
			w_change = pluralizer(week_change, "town_cases")
			week_change_all = week_change_all + week_change
			week_death = df_case_town_filter['total_deaths'].iloc[5]
			week_death_change = week_death_change + int(week_death)
			town_case = f"<li>{w_change} positive for Covid over the last <b>{wdl}</b> (from {week_total} people to {current_total} people).</li>"
			town_case_full = town_case_full + town_case
			town_case_summary = town_case_summary + town_case

			# twenty-eight day count
			case_month_date = df_case_town_filter['date'].iloc[19]
			cmd = human_date(str(case_month_date)[:10])
			month_day_lapse = case_current_date - case_month_date
			mdl = clean_timedelta(month_day_lapse)
			month_total = df_case_town_filter['total_cases'].iloc[19]
			month_change = int(current_total) - int(month_total)
			m_change = pluralizer(month_change, "town_cases")
			month_change_all = month_change_all + month_change
			month_death = df_case_town_filter['total_deaths'].iloc[19]
			month_death_change = month_death_change + int(month_death)
			town_case = f"<li>{m_change} positive for Covid over the last <b>{mdl}</b> (from {month_total} people to {current_total} people).</li></ul>"
			town_case_full = town_case_full + town_case
			town_case_summary = town_case_summary + town_case
			# create table going back X days
			# get code from line 961
			# town_case_full = town_case_full + case_table
			named_anchor = ''.join(t.split()).lower()
			named_anchor = f'id="{named_anchor}-cases"'
			cases_header = f'\n<table {named_anchor}><tr class="cases"><th> Reported date </th><th> Total cases </th><th> New cases </th><th> Total deaths </th><th> New deaths </th></tr>'
			casesline = cases_header
			# rework this to use df_case_town_filter
			case_rows = range(0, case_initial - 1)
			for case_row in case_rows:
				reported_date = str(df_case_town_filter['date'].iloc[case_row])[:10]
				positive_cases = df_case_town_filter['total_cases'].iloc[case_row]
				new_cases = df_case_town_filter['case_change'].iloc[case_row]
				deaths = df_case_town_filter['total_deaths'].iloc[case_row]
				new_deaths = df_case_town_filter['death_change'].iloc[case_row]
				casesline = casesline + f"<tr><td>{reported_date}</td><td>{positive_cases}</td><td>{new_cases}</td><td>{deaths}</td><td>{new_deaths}</td></tr>\n"

			town_case_full = town_case_full + casesline + "</table>"

			#####################
			## Get Vax Numbers ##
			#####################
			rdl = []
			df_vax_filter = df_vax[(df_vax['town'] == t)]
			named_anchor_vax = ''.join(t.split()).lower()
			named_anchor_vax = f'id="{named_anchor_vax}-vaccination"'
			town_vax_text = f"<h3 {named_anchor_vax}>Vaccination percent by age in {t}</h3>\n"
			town_vax_text_summary = f"<h3>Vaccination percent by age in {t}</h3>\n"
			# get dates of all reports in the dataset
			dates_unique = df_vax_filter.reported_date.unique()
			for du in dates_unique:
				rdl.append(du)
			rdl.sort(reverse=True)
			vax_report_date_list = rdl[:vax_initial]
			vaxcount = 0
			summary_vax_text = ""
			for v in vax_report_date_list:
				vaxcount += 1
				datefilter = str(v)[:10]
				df_vaxfilter_town_date = df_vax_filter[df_vax_filter['reported_date'] == datefilter]
				vax_header = f'<p><strong>Reported on {datefilter}</strong></p><table><tr class="vax"><th> Age range </th><th> % Initiated vaccination </th><th> % Fully vaccinated </th></tr>'
				vaxline = ""
				for c,d in df_vaxfilter_town_date.iterrows():
					reporting_town = d['town']
					reported_on = d['reported_date']
					age_range = d['age_group']
					initiated = d['initiated']
					vaccinated = d['vaccinated']
					vaxline = vaxline + f"<tr><td><strong>{age_range}</strong></td><td>{initiated}</td><td>{vaccinated}</td></tr>"
					vax_date = vax_header + "\n" + vaxline + "</table>"
				if vaxcount == 1:
					town_case_summary = town_case_summary + town_vax_text_summary + vax_date
				else:
					pass
				town_vax_text = town_vax_text + vax_date
			town_case_full = town_case_full + town_vax_text

		cc_all = pluralizer(case_change_all, "town_cases")
		wc_all = pluralizer(week_change_all, "town_cases")
		mc_all = pluralizer(month_change_all, "town_cases")


		all_town_summary = f"<h3>In {alltowns}</h3><p>As of <b>{ccd}</b>:</p><ul>"
		all_town_summary = all_town_summary + f"<li>{cc_all} positive for Covid over the last <b>{tbr}</b>;</li>"
		all_town_summary = all_town_summary + f"<li>{wc_all} positive for Covid over the last <b>{wdl}</b>;</li>"
		all_town_summary = all_town_summary + f"<li>{mc_all} positive for Covid over the last <b>{mdl}</b>.</li>"
		all_town_summary = all_town_summary + "</ul>"

		total_population = "{:,}".format(total_population)
		summary_pop = f"{total_population} people live in <b>{alltowns}</b>."

		title = f"Covid19 Vaccination Levels and Positive Cases in {alltowns}, Current on {ccd}" # Report Title
		blog_title = f"Daily Summary for {alltowns}, for {ccd}" # Blog post title

	county_text_all = ""
	for f in fips_code:
		df_fips_filter = df_fips[(df_fips['fips_code'] == f)]
		df_fips_filter.sort_values(by=['report_date'], inplace=True, ascending=False)
		county_rep_date = df_fips_filter['report_date'].iloc[0]
		crd = human_date(str(county_rep_date)[:10])
		county_name = df_fips_filter['county_name'].iloc[0] 
		county_text = f"<h3>Case and Transmission Levels in {county_name}</h3><p>In {county_name}:"
		county_line = ""
		# get current values
		seven_day = df_fips_filter['seven_day'].iloc[0]
		positivity = df_fips_filter['positivity'].iloc[0]
		level = df_fips_filter['level'].iloc[0]
		county_line = f"<ul><li>On <b>{crd}</b>, the seven day rate was <b>{seven_day} cases per 100k people</b>.</li><ul><li>Test positivity: <b>{positivity}%</b></li><li>Community transmission level: <b>{level}</b></li></ul></ul>"
		county_text = county_text + county_line

		# get 7 day values
		seven_date = df_fips_filter['report_date'].iloc[7]
		sdd = human_date(str(seven_date)[:10])
		seven_seven_day = df_fips_filter['seven_day'].iloc[7]
		seven_positivity = df_fips_filter['positivity'].iloc[7]
		seven_level = df_fips_filter['level'].iloc[7]
		week_change = county_rep_date - seven_date
		week_c = clean_timedelta(week_change)
		county_line = f"<ul><li>On {sdd}, <b>{week_c} ago</b>, the seven day rate was <b>{seven_seven_day} cases per 100k people</b>.</li><ul><li>Test positivity: <b>{seven_positivity}%</b></li><li>Community transmission level: <b>{seven_level}</b></li></ul></ul>"
		county_text = county_text + county_line

		# get 28 day values
		twentyeight_date = df_fips_filter['report_date'].iloc[28]
		ted = human_date(str(twentyeight_date)[:10])
		twentyeight_seven_day = df_fips_filter['seven_day'].iloc[28]
		twentyeight_positivity = df_fips_filter['positivity'].iloc[28]
		twentyeight_level = df_fips_filter['level'].iloc[28]
		month_change = county_rep_date - twentyeight_date
		month_c = clean_timedelta(month_change)
		county_line = f"<ul><li>On {ted}, <b>{month_c} ago</b>, the seven day rate was <b>{twentyeight_seven_day} cases per 100k people</b>.</li><ul><li>Test positivity: <b>{twentyeight_positivity}%</b></li><li>Community transmission level: <b>{twentyeight_level}</b></li></ul></ul></p>"
		county_text = county_text + county_line
		county_text_all = county_text_all + county_text
	summary_pop = f"<p>{summary_pop} {alltowns} are part of <b>{county_name}</b>.</p>"


	hosp_text = ""
	for cr in counties_report:
		# Filter by county
		cr = cr + " County"
		df_hosp_filter = df_hospital[df_hospital['county_name'] == cr]
		df_hosp_filter.sort_values(by=['date_updated'], inplace=True, ascending=False)
		# get most recent report
		hosp_date = df_hosp_filter['date_updated'].iloc[0]
		gap_delta = hosp_date - df_hosp_filter['date_updated'].iloc[1]
		gd = clean_timedelta(gap_delta)
		h_date = human_date(str(hosp_date))
		hd_one = df_hosp_filter['date_updated'].iloc[0]
		hosp_total = df_hosp_filter['hosp_cases'].iloc[0]
		hosp_new = df_hosp_filter['new_hosp'].iloc[0]
		h_new = pluralizer(hosp_new, "hospital")
		hosp_text = hosp_text + "<h3>Hospitalizations in " + cr + "</h3>"
		
		hosp_text = hosp_text + f"<ul><li>In {cr}, in the <b>{gd} before</b> {h_date}, {h_new} hospitalized with Covid.</li>"
		
		# get counts for the last approx 7 days
		week_hosp_date = df_hosp_filter['date_updated'].iloc[5]
		hd_week = df_hosp_filter['date_updated'].iloc[5]
		week_hosp_total = df_hosp_filter['hosp_cases'].iloc[5]
		week_hosp_new = hosp_total - week_hosp_total
		w_new = pluralizer(week_hosp_new, "hospital")
		week_change = hd_one - hd_week
		wkc = clean_timedelta(week_change)
		hosp_text = hosp_text + f"<li>Over the last <b>{wkc}</b>, {w_new} hospitalized with Covid (from {week_hosp_total} to {hosp_total} people).</li>"

		# get counts for approx the last 28 days
		month_hosp_date = df_hosp_filter['date_updated'].iloc[19]
		hd_month = df_hosp_filter['date_updated'].iloc[19]
		month_hosp_total = df_hosp_filter['hosp_cases'].iloc[19]
		month_hosp_new = hosp_total - month_hosp_total
		m_new = pluralizer(month_hosp_new, "hospital")
		month_change = hd_one - hd_month
		mtc = clean_timedelta(month_change)
		hosp_text = hosp_text + f"<li>Over the last <b>{mtc}</b>, {m_new} hospitalized with Covid (from {month_hosp_total} to {hosp_total} people).</li></ul>"
			
	## Schools
	## This section is largely manual - blech
	## Read in intro text from file
	if run_schools == "yes":
		school_num = str(len(town_list) + 2)
		schools_text_header = f'<h2 id="schools">{school_num}. Positive Cases in Schools</h2>'
		print(f"Processing school data.\n")
		with open(school_intro) as f:
			schools_text = f.read()

		with open(school_cases) as input:
			df_school_data = pd.read_csv(input)

		school_case_header = f'\n<table><tr class="cases"><th> Reported Date </th><th> Cases </th><th> School </th><th> Notes or Explanations </th></tr>'
		school_case_count = 0
		school_count_interval = 0
		for r, s in df_school_data.iterrows():
			school_date = s['date']
			cases = s['cases']
			school_case_count = school_case_count + int(cases)
			fourteen_dl_raw = [case_current_date - dt.timedelta(days=x) for x in range(14)]
			fourteen_dl_raw = set(fourteen_dl_raw)
			fourteen_dl_raw = (list(fourteen_dl_raw))
			fourteen_dl_raw.sort(reverse=True)
			clean_string_fourteen_dl = []
			for l in fourteen_dl_raw:
				l_clean = str(l).split(" ")[0]
				clean_string_fourteen_dl.append(l_clean)
			if school_date in clean_string_fourteen_dl:
				school_count_interval = school_count_interval + int(cases)
			else:
				pass
			school = s['school']
			notes = s['notes']
			if notes == "none":
				notes = ""
			else:
				pass
			school_line = f"<tr><td>{school_date}</td><td>{cases}</td><td>{school}</td><td>{notes}</td></tr>"
			school_case_header = school_case_header + school_line
		# data prep for human-friendly versions
		sdb = datetime.strptime(clean_string_fourteen_dl[0], '%Y-%m-%d')
		sd_begin = sdb.strftime("%b %d, %Y")
		sde = datetime.strptime(clean_string_fourteen_dl[-1], '%Y-%m-%d')
		sd_end = sde.strftime("%b %d, %Y")
		school_case_interval = f"<p>In the <b>{len(clean_string_fourteen_dl)} days</b> between {sd_begin} and {sd_end}, Lyme-Old Lyme Regional School District 18 has disclosed knowledge of <b>{school_count_interval} people</b> in the schools with Covid.</p>"
		school_cases_text = f'<p>As of {sd_begin}, the district superintendent has disclosed that <b>{str(school_case_count)} people in Lyme-Old Lyme Schools</b> have tested positive for Covid in the 2021-2022 school year.</p>'
		schools_full = schools_text_header + school_case_interval + school_cases_text + schools_text + school_case_header + "</table>"
	else:
		schools_full = ""
		school_case_interval = ""
## Finalize reports
	report_full = report_intro + summary_pop + all_town_summary + school_case_interval + county_text_all + hosp_text + anchor_links + town_case_full + schools_full
	report_intro = report_intro + summary_pop + all_town_summary + school_case_interval + county_text_all + hosp_text + town_case_summary
	
	if export_html == "yes":
		report_full_html = "<h2>" + title + "</h2>" + report_full
		report_intro_html = "<h2>" + blog_title + "</h2>" + report_intro
		if add_style == "yes":
			with open(style_declaration) as f:
				style = f.read()
				report_intro_html = style + report_intro_html
				report_full_html = style + report_full_html
		else:
			pass
		htmlfile = output_file + "_" + scan_datetime + ".html"
		with open(report_dir + htmlfile, 'w') as g:
			g.write(report_full_html)

		introfile = output_file + "_blog_" + scan_datetime + ".html"
		with open(report_dir + introfile, 'w') as g:
			g.write(report_intro_html)
	else:
		pass
## Update detailed report page
	if export_update == "yes":
		print(f" ** Updating the site. This might take a minute.")

		credentials = user + ':' + password
		token = base64.b64encode(credentials.encode())
		header = {'Authorization': 'Basic ' + token.decode('utf-8')}

		if add_style == "yes":
			with open(style_declaration) as f:
				style = f.read()
				report_full = style + report_full
		else:
			pass

		## update the page
		page = {
			'title':title,
			'content':report_full
		}
		response_page = requests.post(url_page + pageID , headers=header, json=page)

		# post summary blog
		if str(response_page) == "<Response [200]>":
			print(f" ** The page titled '{title}' updated sucessfully,\n")
		else: 
			print(f"There seems to be an issue with the update. This was the response code:\n{response}")
	else:
		pass
## Create blog post
	if create_blog == "yes":
		print(f" ** Creating a blog post. This might take a minute.")
		read_full_report = f'<p>For more background information, see the <a href="{detailed_report_url}" title="Full report of current data on Covid cases and vaccinations">detailed report of current information</a>.</p>'

		credentials = user + ':' + password
		token = base64.b64encode(credentials.encode())
		header = {'Authorization': 'Basic ' + token.decode('utf-8')}

		if add_style == "yes":
			with open(style_declaration) as f:
				style = f.read()
				report_intro = style + read_full_report + report_intro
		else:
			pass

		post = {
			'title':blog_title,
			'status': 'publish', 
			'content': report_intro,
			'categories':category,
			'author':post_author
			}

		response_post = requests.post(url_post, headers=header, json=post)
		if str(response_post) == "<Response [201]>":
			print(f"** The blog post titled '{blog_title}' was created.\n")
		else: 
			print(f"There seems to be an issue with creating the post. This was the response code:\n{response_post}")
	else:
		pass

#	print(report_full)

#df_cases.to_csv('all_cases.csv', encoding='utf-8', index=False)
#df_vax.to_csv('all_vax.csv', encoding='utf-8', index=False)
#df_fips.to_csv('all_fips.csv', encoding='utf-8', index=False)
#df_hospital.to_csv('all_hospital.csv', encoding='utf-8', index=False)

print("Done!")