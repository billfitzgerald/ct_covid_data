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
#batch_files = ['ct_river_area.json', 'ledgelight.json', 'lyme_oldlyme.json']
batch_files = ['ct_river_area.json', 'lyme_oldlyme.json']
export_to_wordpress = "no"

## External sources
opening = "source/opening.txt"
data_intro = "source/data_intro.txt"
style_declaration = "source/style.txt"
creds = "creds/creds_batch.ini"
population = "source/ct_population.csv"

### Case-specific information
case_initial = 6 # number of most recent reports to show
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

def clean_timedelta(td):
	# this is brittle; it assumes 00:00:00
	td_list = str(td).split(" 00:")
	clean_td = td_list[0]
	return clean_td

def unique_list(raw_list):
	# insert the list to the set
	list_set = set(raw_list)
	# convert the set to the list
	unique_list = (list(list_set))
	return unique_list

def list_clean(list_items):
	holding=[]
	for l in list_items:
		l_clean = str(l).split(" ")[0]
		holding.append(l_clean)
	return(holding)


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

# vax date values - generally no need to adjust this unless you want a longer time interval
#startdate = '2021-03-17T00:00:00'
startdate = forty_five_prior
enddate = current

#case values - generally no need to adjust this unless you want a longer time interval
#startcase = '2021-03-17T00:00:00'
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
		title = f"Covid19 Vaccination Levels and Positive Cases in {alltowns}" # Report Title
		blog_title = f"Daily Summary for {alltowns}" # Blog post title
		with open(data_intro) as di:
			intro_text = di.read()
		blog_source = intro_text
		report_intro = intro_text + "<h2>1. Overview</h2>" + batch_desc
		# Set link to named anchors
		anchor_links = "<h3>Jump to detailed reports:</h3><ul>"
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
		town_list = data['town_list']
		fips_code = data['fips_code']
		for f in fips_code:
			print(f)
			for key,value in county_fips_dict.items():
				if key == f:
					counties_report.append(value)
				else:
					pass
		#print(town_list)
		#print(fips_code)
		#print(counties_report)
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
			ccd = human_date(str(case_current_date)[:10])
			current_change = df_case_town_filter['case_change'].iloc[0]
			case_change_all = case_change_all + int(current_change)
			current_total = df_case_town_filter['total_cases'].iloc[0]
			yesterday_total = df_case_town_filter['total_cases'].iloc[1]
			current_death = df_case_town_filter['total_deaths'].iloc[0]
			town_case = f"<ul><li>On {ccd}: a change of <b>{current_change} cases</b> over 24 hours, from {yesterday_total} people to {current_total} people.</li>"
			town_case_full = town_case_full + town_title + town_case
			town_case_summary = town_case_summary + opening_title + town_case

			# seven day count
			case_week_date = df_case_town_filter['date'].iloc[5]
			cwd = human_date(str(case_week_date)[:10])
			week_day_lapse = case_current_date - case_week_date
			wdl = clean_timedelta(week_day_lapse)
			week_total = df_case_town_filter['total_cases'].iloc[5]
			week_change = int(current_total) - int(week_total)
			week_change_all = week_change_all + week_change
			week_death = df_case_town_filter['total_deaths'].iloc[5]
			week_death_change = week_death_change + int(week_death)
			town_case = f"<li>In the last {wdl}: a change of <b>{week_change} cases</b>, from {week_total} people to {current_total} people.</li>"
			town_case_full = town_case_full + town_case
			town_case_summary = town_case_summary + town_case

			# twenty-eight day count
			case_month_date = df_case_town_filter['date'].iloc[19]
			cmd = human_date(str(case_month_date)[:10])
			month_day_lapse = case_current_date - case_month_date
			mdl = clean_timedelta(month_day_lapse)
			month_total = df_case_town_filter['total_cases'].iloc[19]
			month_change = int(current_total) - int(month_total)
			month_change_all = month_change_all + month_change
			month_death = df_case_town_filter['total_deaths'].iloc[19]
			month_death_change = month_death_change + int(month_death)
			town_case = f"<li>In the last {mdl}: a change of {month_change} cases, from {month_total} people to {current_total} people.</li></ul>"
			town_case_full = town_case_full + town_case
			town_case_summary = town_case_summary + town_case

			#####################
			## Get Vax Numbers ##
			#####################
			rdl = []
			df_vax_filter = df_vax[(df_vax['town'] == t)]
			named_anchor_vax = ''.join(t.split()).lower()
			named_anchor_vax = f'id="{named_anchor_vax}-vaccination"'
			town_vax_text = f"<h3 {named_anchor_vax}>Vaccination percent by age in {t}</h3>\n"
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
					town_case_summary = town_case_summary + vax_date
				else:
					pass
				town_vax_text = town_vax_text + vax_date
			town_case_full = town_case_full + town_vax_text

		all_town_summary = f"<h3>In {alltowns}</h3><ul>"
		all_town_summary = all_town_summary + f"<li>24 hour change in {alltowns}: {case_change_all}</li>"
		all_town_summary = all_town_summary + f"<li>{week_day_lapse} change in {alltowns}: {week_change_all}</li>"
		all_town_summary = all_town_summary + f"<li>{month_day_lapse} change in {alltowns}: {month_change_all}</li>"
		all_town_summary = all_town_summary + "</ul>"

		total_population = "{:,}".format(total_population)
		summary_pop = f"{total_population} people live in <b>{alltowns}</b>."	

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
	print(county_text_all)
	summary_pop = f"<p>{summary_pop} {alltowns} are part of <b>{county_name}</b>.</p>"


	hosp_text = ""
	for cr in counties_report:
		# Filter by county
		cr = cr + " County"
		df_hosp_filter = df_hospital[df_hospital['county_name'] == cr]
		df_hosp_filter.sort_values(by=['date_updated'], inplace=True, ascending=False)
		# get most recent report
		hosp_date = df_hosp_filter['date_updated'].iloc[0]
		hd_one = df_hosp_filter['date_updated'].iloc[0]
		hosp_total = df_hosp_filter['hosp_cases'].iloc[0]
		hosp_new = df_hosp_filter['new_hosp'].iloc[0]
		hosp_text = hosp_text + "<h3>Hospitalizations in " + cr + "</h3>"
		if hosp_new > 0:
			whn_text = f"<b>{hosp_new} additional people</b> were"
		elif hosp_new == 0:
			whn_text = f"there has been <b>no change</b> in the number of people"
		else:
			whn_count = int(hosp_new) * -1
			whn_text = f"<b>{whn_count} fewer people</b> are"
		hosp_text = hosp_text + f"<ul><li>In {cr}, in the <b>24 hours before</b> {hosp_date}, {whn_text} hospitalized with Covid.</li>"
		
		# get counts for the last approx 7 days
		week_hosp_date = df_hosp_filter['date_updated'].iloc[5]
		hd_week = df_hosp_filter['date_updated'].iloc[5]
		week_hosp_total = df_hosp_filter['hosp_cases'].iloc[5]
		week_hosp_new = hosp_total - week_hosp_total
		if week_hosp_new > 0:
			whn_text = f"<b>{week_hosp_new} additional people</b> were"
		elif week_hosp_new == 0:
			whn_text = f"there has been <b>no change</b> in the number of people"
		else:
			whn_count = int(week_hosp_new) * -1
			whn_text = f"<b>{whn_count} fewer people</b> are"
		week_change = hd_one - hd_week
		wkc = clean_timedelta(week_change)
		hosp_text = hosp_text + f"<li>Over the last <b>{wkc}</b>, {whn_text} hospitalized with Covid.</li>"
		print(week_hosp_total)
		print(week_hosp_new) # last 6 reports

		# get counts for approx the last 28 days
		month_hosp_date = df_hosp_filter['date_updated'].iloc[19]
		hd_month = df_hosp_filter['date_updated'].iloc[19]
		month_hosp_total = df_hosp_filter['hosp_cases'].iloc[19]
		month_hosp_new = hosp_total - month_hosp_total
		month_change = hd_one - hd_month
		mtc = clean_timedelta(month_change)
		if month_hosp_new > 0:
			whn_text = f"<b>{month_hosp_new} additional people</b> were"
		elif month_hosp_new == 0:
			whn_text = f"there has been <b>no change</b> in the number of people"
		else:
			whn_count = int(month_hosp_new) * -1
			whn_text = f"<b>{whn_count} fewer people</b> are"
		hosp_text = hosp_text + f"<li>Over the last <b>{mtc[0]}</b>, {whn_text} hospitalized with Covid.</li></ul>"
			
		print(hosp_text)
	report_intro = report_intro + summary_pop + all_town_summary + county_text_all + hosp_text + town_case_summary
	print(report_intro)

#df_cases.sort_values(by=['date'], inplace=True, ascending=False)
#df_vax.sort_values(by=['reported_date'], inplace=True, ascending=False)
#df_fips.sort_values(by=['report_date'], inplace=True, ascending=False)
#df_hospital.sort_values(by=['date_updated'], inplace=True, ascending=False)

#df_cases.to_csv('all_cases.csv', encoding='utf-8', index=False)
#df_vax.to_csv('all_vax.csv', encoding='utf-8', index=False)
#df_fips.to_csv('all_fips.csv', encoding='utf-8', index=False)
#df_hospital.to_csv('all_hospital.csv', encoding='utf-8', index=False)

#print(df_cases.dtypes)
#print(df_vax.dtypes)
#print(df_fips.dtypes)
#print(df_hospital.dtypes)


#print(towns_for_query)
#print(fips_for_query)
'''
### all old logic below here
		df_vax = df_vax[0:0]
		df_cases = df_cases[0:0]
		df_report = df_report[0:0]
		df_fips = df_fips[0:0]
		df_hospital = df_hospital[0:0]
		total_population = 0
		run_time = f"This report was generated on {nowoclock} at {hour}:{minute}. "
		
		
		if len(batch_desc) > 2:
			batch_desc = f"<p>{batch_desc}</p>"
		
		if run_cdc == "yes":
			
			fcdate = []
			county_name_list = []
			for fc in fips_code:
				print(f" ** Getting county-level transmission data from the CDC\n")
				fips_url = f"https://data.cdc.gov/resource/8396-v7yb.json?fips_code={fc}&$where=report_date%20between%20'{week_prior}'%20and%20'{current}'"
				fips_data = json.loads(requests.get(fips_url).text)
				for fd in fips_data:
					county_name = fd['county_name']
					if county_name not in county_name_list:
						county_name_list.append(county_name)
					report_date = fd['report_date']
					seven_day = fd['cases_per_100k_7_day_count']
					try:
						positivity = fd['percent_test_results_reported']
					except:
						positivity = "not reported"
					level = fd['community_transmission_level']
					fips_obj = pd.Series([county_name, fc, report_date, seven_day, positivity, level], index=df_fips.columns)
					df_fips = df_fips.append(fips_obj, ignore_index=True)
					if fd['report_date'] not in fcdate:
						fcdate.append(fd['report_date'])
			county_text = ""
			x = len(county_name_list)
			if x == 1:
				for cnl in county_name_list:
					hospital_data = hosp_collect(cnl, forty_five_prior, current)
					df_hosp = df_hosp[0:0]
					for hd in hospital_data:
						county_name = cnl
						date_updated = hd['dateupdated']
						hosp_cases = int(hd['hospitalization'])
						new_hosp = 0
						hosp_list = []
						hosp_obj = pd.Series([county_name, date_updated, hosp_cases, new_hosp], index=df_hosp.columns)
						df_hosp = df_hosp.append(hosp_obj, ignore_index=True)
					difference = df_hosp['hosp_cases'].diff()
					df_hosp['new_hosp'] = difference
					df_hospital = df_hospital.append(df_hosp)
					county_text = county_text + cnl
				county_text = f"{alltowns} are part of {county_text}."
			elif x == 2:
				count = 0
				for cnl in county_name_list:
					hospital_data = hosp_collect(cnl, forty_five_prior, current)
					df_hosp = df_hosp[0:0]
					for hd in hospital_data:
						county_name = cnl
						date_updated = hd['dateupdated']
						hosp_cases = int(hd['hospitalization'])
						new_hosp = 0
						hosp_list = []
						hosp_obj = pd.Series([county_name, date_updated, hosp_cases, new_hosp], index=df_hosp.columns)
						df_hosp = df_hosp.append(hosp_obj, ignore_index=True)

					difference = df_hosp['hosp_cases'].diff()
					df_hosp['new_hosp'] = difference
					df_hospital = df_hospital.append(df_hosp)
					count += 1
					if count < x:
						county_text = county_text + cnl + " and "
					elif count == x:
						county_text = county_text + cnl
					else:
						print("Should not be possible. Examine!")
				county_text = f"{alltowns} are part of {county_text}. "
			elif x > 2:
				count = 0
				for cnl in county_name_list:
					hospital_data = hosp_collect(cnl, forty_five_prior, current)
					df_hosp = df_hosp[0:0]
					for hd in hospital_data:
						county_name = cnl
						date_updated = hd['dateupdated']
						hosp_cases = int(hd['hospitalization'])
						new_hosp = 0
						hosp_list = []
						hosp_obj = pd.Series([county_name, date_updated, hosp_cases, new_hosp], index=df_hosp.columns)
						df_hosp = df_hosp.append(hosp_obj, ignore_index=True)
					difference = df_hosp['hosp_cases'].diff()
					df_hosp['new_hosp'] = difference
					df_hospital = df_hospital.append(df_hosp)
					count += 1
					if count < x:
						county_text = county_text + cnl + ", "
					elif count == x:
						county_text = county_text + "and " + cnl
					else:
						print("Should not be possible. Examine!")
				county_text = f"{alltowns} are part of {county_text}. "
			else:
				county_text = "No county names returned. Please review FIPS Code values."
			df_hospital.sort_values(by=['date_updated'], inplace=True, ascending=False)
			county_list = df_hospital.county_name.unique()
			print(county_list)
			hosp_text = ""
			for cl in county_list:
				# Filter by county
				df_hosp_filter = df_hospital[df_hospital['county_name'] == cl]

				# get most recent report
				hosp_date = human_date(df_hosp_filter['date_updated'].iloc[0])
				hd_one = datetime.strptime(df_hosp_filter['date_updated'].iloc[0][:10], '%Y-%m-%d')
				hosp_total = df_hosp_filter['hosp_cases'].iloc[0]
				hosp_new = df_hosp_filter['new_hosp'].iloc[0]
				print(cl)
				print(hosp_date)
				print(hosp_total)
				print(hosp_new) # last 24 hours
				if hosp_new > 0:
					whn_text = f"<b>{hosp_new} additional people</b> were"
				elif hosp_new == 0:
					whn_text = f"there has been <b>no change</b> in the number of people"
				else:
					whn_count = int(hosp_new) * -1
					whn_text = f"<b>{whn_count} fewer people</b> are"
				hosp_text = hosp_text + f"<p>In {cl}, on {hosp_date}, {whn_text} hospitalized with Covid over the last 24 hours. "
				
				# get counts for the last approx 7 days
				week_hosp_date = human_date(df_hosp_filter['date_updated'].iloc[5])
				hd_week = datetime.strptime(df_hosp_filter['date_updated'].iloc[5][:10], '%Y-%m-%d')
				week_hosp_total = df_hosp_filter['hosp_cases'].iloc[5]
				week_hosp_new = hosp_total - week_hosp_total
				if week_hosp_new > 0:
					whn_text = f"<b>{week_hosp_new} additional people</b> were"
				elif week_hosp_new == 0:
					whn_text = f"there has been <b>no change</b> in the number of people"
				else:
					whn_count = int(week_hosp_new) * -1
					whn_text = f"<b>{whn_count} fewer people</b> are"
				week_change = hd_one - hd_week
				wkc = str(week_change).split(',')
				hosp_text = hosp_text + f"Over the last {wkc[0]}, {whn_text} hospitalized with Covid. "
				print(week_hosp_total)
				print(week_hosp_new) # last 6 reports

				# get counts for approx the last 28 days
				month_hosp_date = df_hosp_filter['date_updated'].iloc[19]
				hd_month = datetime.strptime(df_hosp_filter['date_updated'].iloc[19][:10], '%Y-%m-%d')
				month_hosp_total = df_hosp_filter['hosp_cases'].iloc[19]
				month_hosp_new = hosp_total - month_hosp_total
				month_change = hd_one - hd_month
				mtc = str(month_change).split(',')
				print(month_hosp_total)
				print(month_hosp_new) #last 27 reports
				if month_hosp_new > 0:
					whn_text = f"<b>{month_hosp_new} additional people</b> were"
				elif month_hosp_new == 0:
					whn_text = f"there has been <b>no change</b> in the number of people"
				else:
					whn_count = int(month_hosp_new) * -1
					whn_text = f"<b>{whn_count} fewer people</b> are"
				hosp_text = hosp_text + f"Over the last {mtc[0]}, {whn_text} hospitalized with Covid.</p>"
				
				print(hosp_text)
			# In X County, on X date, X people are hospitalized with Covid. This is an increase/decrease of X since DATE.

			fcdate.sort(reverse=True)
			df_fips_filter = df_fips[(df_fips['report_date'] == fcdate[0])]
			county_rep_date = fcdate[0][:10]
			county_text = f"<p><b>{county_text}</b> County data reported on <b>{county_rep_date}</b>.</p>"
			county_line = ""
			for a,b in df_fips_filter.iterrows():
				date = b['report_date']
				county = b['county_name']
				seven_day = b['seven_day']
				positivity = b['positivity']
				level = b['level']
				county_line = f"<p>{county_line}{county} has a seven day rate of <b>{seven_day} cases per 100k people</b>.<ul><li>Test positivity: <b>{positivity}%</b></li><li>Community transmission level: <b>{level}</b></li></ul></p>"
			county_text = county_text + county_line

### Get for schools and reports
		run_schools = data['run_schools']
		ifschools = data['ifschools']
		school_intro = data['school_intro']
		school_cases = data['school_cases']
		pageID = data['pageID']
		category = data['categoryID']
		post_author = data['post_author']
		output_file = data['output']
		detailed_report_url = data['detailed_report_url']
		# Set initial reporting language
		title = f"Covid19 Vaccination Levels and Positive Cases in {alltowns}"
		blog_title = f"Daily Summary for {alltowns}"
		with open(data_intro) as di:
			intro_text = di.read()
		blog_source = intro_text
		report_intro = intro_text + "<h2>1. Overview</h2>" + batch_desc + county_text
		report_summary = ""
		# Set link to named anchors
		anchor_links = "<h3>Jump to detailed reports:</h3><ul>"
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

		# vax data source: https://data.ct.gov/Health-and-Human-Services/COVID-19-Vaccinations-by-Town-and-Age-Group/gngw-ukpw
		# https://data.ct.gov/resource/gngw-ukpw.json?town=Lyme&$where=dateupdated between '2021-10-17T00:00:00' and '2021-11-24T00:00:00'
		# populate vax dataframe with all data 
		rdl = []
		enddate_str = enddate[:10]
		for t in town_list:
			print(f"   * Getting vaccination rate data for {t}\n")
			vax_url = f"https://data.ct.gov/resource/gngw-ukpw.json?town={t}&$where=dateupdated%20between%20'{startdate}'%20and%20'{enddate}'"
			vax_data = json.loads(requests.get(vax_url).text)
			for v in vax_data:
				town = v['town']
				reported_date = v['dateupdated'][:10]
				age_group = v['age_group']
				initiated = v['initiated_vaccination_percent']
				vaccinated = v['fully_vaccinated_percent']
				vax_obj = pd.Series([town, reported_date, age_group, initiated, vaccinated], index=df_vax.columns)
				df_vax = df_vax.append(vax_obj, ignore_index=True)
		# filter dataframe and get counts for each town
		blog_vax_text = ""
		for t in town_list:
			vaxcount = 0
			df_vax_filter = df_vax[(df_vax['town'] == t)]
			named_anchor_vax = ''.join(t.split()).lower()
			named_anchor_vax = f'id="{named_anchor_vax}-vaccination"'
			town_case_text = f"<h3 {named_anchor_vax}>Vaccination percent by age in {t}</h3>\n"
			blog_vax = town_case_text
			# get dates of all reports in the dataset
			for a, b in df_vax_filter.iterrows():
				report_date = datetime.strptime(b['reported_date'], '%Y-%m-%d')
				if report_date not in rdl:
					rdl.append(report_date)
	# sort dates with most recent first
				rdl.sort(reverse=True)
				vax_report_date_list = rdl[:vax_initial]
			vax_current_report_date = rdl[0].strftime("%b %d, %Y")
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
					## This is not currently used, but it could support tracking changes in
					## vaccination rates over time
					vax_date = vax_header + "\n" + vaxline + "</table>"
				town_case_text = town_case_text + vax_date
				if vaxcount == 1:
					blog_vax = blog_vax + vax_date
					blog_vax_text = blog_vax_text + blog_vax
				else:
					pass
			obj_report = pd.Series([t, town_case_text, "ca"], index=df_report.columns)
			df_report = df_report.append(obj_report, ignore_index=True)
			run_time = run_time + f'The most recent data on vaccination reports included here is from <b>{vax_current_report_date}</b>. '

		# case data by source: https://data.ct.gov/Health-and-Human-Services/COVID-19-Tests-Cases-and-Deaths-By-Town-/28fr-iqnx
		# https://data.ct.gov/resource/28fr-iqnx.json?town=Lyme&$where=lastupdatedate between '2021-10-30T00:00:00' and '2021-11-30T00:00:00'
		# populate cases dataframe with all data

		cdl = []
		endcase_str = endcase[:10]
		case_calcdate = datetime.strptime(endcase_str, '%Y-%m-%d')
		for t in town_list:
			df_ca_tmp = df_ca_tmp[0:0]
			print(f"   - Getting case and death rate data for {t}\n")
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
			print(difference)
			df_ca_tmp['case_change'] = case_difference
			df_ca_tmp['death_change'] = death_difference
			df_cases = df_cases.append(df_ca_tmp)
		print(df_cases)
	# filter dataset by town and get counts
		blog_cases = ""
		one_count = 0
		two_count = 0
		for t in town_list:
			# Get population for the town
			df_pop_filter = df_population[(df_population['town'] == t)]
			town_pop = df_pop_filter['pop'].iloc[0]
			tp = int(town_pop)
			total_population = total_population + tp
			tp = "{:,}".format(tp)
			# Get cases for the town
			df_cases_filter = df_cases[(df_cases['town'] == t)]
			town_cases_text = ""
			# get dates of all reports in the dataset
			for a, b in df_cases_filter.iterrows():
				report_date = datetime.strptime(b['date'], '%Y-%m-%d')
				if report_date not in cdl:
					cdl.append(report_date)
			# sort dates with most recent first
			cdl.sort(reverse=True)
			case_report_date_list = cdl[:case_initial]
			startd = case_report_date_list[0]
			startd_plus_one = case_report_date_list[1]
			## get day lists - 7 and 14
			seven_dl_raw = [startd - dt.timedelta(days=x) for x in range(7)]
			clean_date_seven_dl = unique_list(seven_dl_raw)
			clean_date_seven_dl.sort(reverse=True)
			clean_string_seven_dl = list_clean(clean_date_seven_dl)
			fourteen_dl_raw = [startd - dt.timedelta(days=x) for x in range(14)]
			clean_date_fourteen_dl = unique_list(fourteen_dl_raw)
			clean_date_fourteen_dl.sort(reverse=True)
			clean_string_fourteen_dl = list_clean(clean_date_fourteen_dl)
			# lists populated; moving on
			human_startd = startd.strftime("%b %d, %Y")
			endd = case_report_date_list[case_initial - 1]
			human_endd = endd.strftime("%b %d, %Y")
			difference = str((startd - endd)).split(',')
			named_anchor = ''.join(t.split()).lower()
			named_anchor = f'id="{named_anchor}-cases"'
			cases_header = f'\n<table {named_anchor}><tr class="cases"><th> Reported date </th><th> Total cases </th><th> New cases </th><th> Total deaths </th><th> New deaths </th></tr>'
			casesline = ""
			for c in case_report_date_list:
				datefilter = str(c)[:10]
				df_cases_bytown = df_cases_filter[df_cases_filter['date'] == datefilter]
				for c,d in df_cases_bytown.iterrows():
					reporting_town = d['town']
					reported_date = d['date']
					positive_cases = d['total_cases']
					new_cases = d['case_change']
					deaths = d['total_deaths']
					new_deaths = d['death_change']
					casesline = casesline + f"<tr><td>{reported_date}</td><td>{positive_cases}</td><td>{new_cases}</td><td>{deaths}</td><td>{new_deaths}</td></tr>\n"
					if datefilter == str(case_report_date_list[0])[:10]:
						base_cases = positive_cases
						base_deaths = deaths
						base_date = datefilter
					elif datefilter == str(case_report_date_list[1])[:10]:
						day_cases = positive_cases
						day_deaths = deaths
						dd = datetime.strptime(datefilter, '%Y-%m-%d')
						day_date = dd.strftime("%b %d, %Y")
						day_diff = str(startd - case_report_date_list[1]).split(',')
					elif datefilter == str(case_report_date_list[case_initial - 1])[:10]:
						end_cases = positive_cases
						end_deaths = deaths
						ed = datetime.strptime(datefilter, '%Y-%m-%d')
						end_date = ed.strftime("%b %d, %Y")
						end_diff = str(startd - case_report_date_list[case_initial - 1]).split(',')
					else:
						pass
			case24 = int(base_cases) - int(day_cases)
			death24 = int(base_deaths) - int(day_deaths)
			one_count = one_count + case24
			if case24 == 1:
				ccl24 = f"{case24} person"
			else:
				ccl24 = f"{case24} people"
			if death24 == 1:
				dcl24 = f"{death24} person"
			else:
				dcl24 = f"{death24} people"
			case_change = int(base_cases) - int(end_cases)
			death_change = int(base_deaths) - int(end_deaths)
			if case_change == 1:
				ccl = f"{case_change} person"
			else:
				ccl = f"{case_change} people"
			if death_change == 1:
				dcl = f"{death_change} person"
			else:
				dcl = f"{death_change} people"
			day_rate = f"<h3>Positive Cases and Deaths in {t}</h3><p>{tp} people live in {t}</p><ul><li>In the <b>{day_diff[0]}</b> between the two most recent reports on {human_startd} and {day_date}, <b>{ccl24} contracted Covid</b>, and <b>{dcl24} died</b> as a result of Covid.</li>"
			if case24 == 0 and death24 == 0:
				day_rate = f"<h3>Positive Cases and Deaths in {t}</h3><p>{tp} people live in {t}</p><ul><li>In the <b>{day_diff[0]}</b> between the two most recent reports, no people have contracted Covid, or died as a result of Covid.</li>"
			else:
				pass
			case_rate = f"<li>In the <b>{difference[0]}</b> between {human_startd} and {end_date}, <b>{ccl} contracted Covid</b> and <b>{dcl} died</b> as a result of Covid.</li></ul>"
			cases_current = day_rate + "\n" + case_rate + "\n" + cases_header + "\n" + casesline + "</table>"
			blog_cases = blog_cases + day_rate + "\n" + case_rate
			town_cases_text = town_cases_text + cases_current + "\n"
			report_summary = report_summary + day_rate + "\n" + case_rate + "\n"
			obj_report = pd.Series([t, town_cases_text, "aa"], index=df_report.columns)
			df_report = df_report.append(obj_report, ignore_index=True)
		## Work through intervals	
			full_interval = ""
			case_header = f'\n<table><tr class="cases"><th> Reported Date </th><th> Total cases </th><th> Deaths </th></tr>'
			caseline = case_header 
			change_text = "<ul>"
			for ci in case_interval: #iterate through interval values; get dates
				key_date = cdl[ci]
				# startd is the most recent report
				difference = str((startd - key_date)).split(',')
				datefilter = str(key_date)[:10]
				df_vaxc_bytown_interval = df_cases_filter[df_cases_filter['date'] == datefilter]
				for c,d in df_vaxc_bytown_interval.iterrows():
					reporting_town = d['town']
					reported_date = d['date']
					positive_cases = d['total_cases']
					deaths = d['total_deaths']
					caseline = caseline + f"<tr><td>{reported_date}</td><td>{positive_cases}</td><td>{deaths}</td></tr>"
					## calculate change
					case_change = int(base_cases) - int(positive_cases)
					death_change = int(base_deaths) - int(deaths)
					hd = datetime.strptime(datefilter, '%Y-%m-%d')
					human_intervaldate = hd.strftime("%b %d, %Y")
					change_text = change_text + f"<li>In the <b>{difference[0]}</b> between {human_startd} and {human_intervaldate}, people in {t} experienced <b>{case_change} additional cases</b> and <b>{death_change} deaths</b>.</li>"
			caseline = caseline + "</table>"
			change_text = change_text + "</ul>"
			full_interval = f"<h3>Cases over time in {t}</h3>" + change_text + caseline
			obj_report = pd.Series([t, full_interval, "ba"], index=df_report.columns)
			df_report = df_report.append(obj_report, ignore_index=True)
		summ_day_diff = startd - startd_plus_one
		summ_day = str(summ_day_diff).split(",")
		day_summary = f"In {alltowns}, {one_count} people have tested positive for Covid in the <b>{summ_day[0]}</b> between {human_startd} and {day_date}."
		run_time = run_time + f'The most recent data on cases and deaths included here is from <b>{human_startd}</b>. '
		blog_title = blog_title + " for " + human_startd
		total_population = "{:,}".format(total_population)
		population_batch = f"<p>{total_population} people live in {alltowns}</p>" 
		report_intro = report_intro + population_batch + day_summary


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
			school_cases_text = f'<p>As of {human_startd}, the district superintendent has disclosed that <b>{str(school_case_count)} people in Lyme-Old Lyme Schools</b> have tested positive for Covid in the 2021-2022 school year.</p>'
			schools_full = schools_text_header + school_case_interval + school_cases_text + schools_text + school_case_header + "</table>"
			report_intro = report_intro + school_case_interval
		else:
			schools_full = ""

		## Generate report
		print(f"--- Generating an html report.\n")
		## Using <style> in this way is Very Not Good
		## These declarations should generally be in the head; because 
		## this doesn't generate a head (or really a body either) I'm 
		## throwing this in the body. It's janky but it works.
		## I'd rather be done than proud.
		with open(style_declaration) as f:
			style = f.read()

		with open(opening) as f:
			intro_blurb = f.read()

		if run_schools == "yes":
			school_opening = f'<h3>Positive Cases in Schools</h3>{school_case_interval}<p>Read the detailed breakdown on <a href="#schools" title="Breakdown of positive cases in schools">Positive Cases in Schools.</a>'
			with open(ifschools) as f:
				school_blurb = f.read()
			report_summary = style + report_summary + school_opening + intro_blurb + school_blurb
		else:
			report_summary = style + report_summary + intro_blurb

		report_summary = report_summary + "<p>" + run_time + "</p>" + anchor_links + "\n<hr>"
		df_report.sort_values(by=['sequence'], inplace=True)
		all_text = ""
		town_count = 1
		for t in town_list:
			town_count += 1
			df_report_filter = df_report[df_report['town'] == t]
			core_text = ""
			for p,q in df_report_filter.iterrows():
				core_text = core_text + q['text']
			named_anchor_town = ''.join(t.split()).lower()
			named_anchor_town = f'id="{named_anchor_town}"'
			all_text = all_text + "<h2 " + named_anchor_town + ">" + str(town_count) + ". " + t + "</h2>" + core_text + "<hr>"
		doc_text = report_intro + report_summary + all_text + schools_full
		htmlfile = output_file + "_" + scan_datetime + ".html"

		with open(report_dir + htmlfile, 'w') as g:
			g.write(f"<h2>{title}</h2>{doc_text}")

		if export_to_wordpress == "yes":
			print(f" ** Updating the site. This might take a minute.")


			credentials = user + ':' + password
			token = base64.b64encode(credentials.encode())
			header = {'Authorization': 'Basic ' + token.decode('utf-8')}

			## update the page
			page = {
				'title':title,
				'content':doc_text
			}
			response_page = requests.post(url_page + pageID , headers=header, json=page)

			# post summary blog
			if str(response_page) == "<Response [200]>":
				print(f" ** The page titled '{title}' updated sucessfully,\n")
			else: 
				print(f"There seems to be an issue with the update. This was the response code:\n{response}")

			blog_full_report = f'See the <a href="{detailed_report_url}" title="Full report of current data on Covid cases and vaccinations">detailed report of current information</a>.'
			blog_content = style + run_time + blog_full_report + report_intro + "<p>" + blog_full_report + "</p>" + blog_cases + blog_vax_text + blog_source

			post = {
				'title':blog_title,
				'status': 'publish', 
				'content': blog_content,
				'categories':category,
				'author':post_author
				}

			response_post = requests.post(url_post, headers=header, json=post)
			if str(response_post) == "<Response [201]>":
				print(f"** The blog post titled '{blog_title}' was created.\n")
			else: 
				print(f"There seems to be an issue with creating the post. This was the response code:\n{response_post}\nThis is the blog text:\n{blog_content}")

		else:
			pass
'''
print("Done!")