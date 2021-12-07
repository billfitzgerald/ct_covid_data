from pprint import pprint
import json
import requests 
import pandas as pd
import os
import datetime as dt
from datetime import datetime
from configparser import ConfigParser
import base64

# Set general variables prior to running
town_list = ['Lyme', 'Old Lyme']
run_vax = "yes" ## leave this as 'yes'
run_cases = "yes" ## leave this as 'yes'
run_schools = "yes"
export_to_wordpress = "yes"
export_to_twitter = "no"
### Case-specific information
case_initial = 6 # number of most recent reports to show
# interval is measured in number of reports. In general, 5 reports come out 
# every 7 days, so to go back 28 days enter 20
case_interval = [10, 20, 64, 128]
### Vax specific information
vax_initial = 3 # number of most recent vax level reports to show

## External sources
opening = "source/opening.txt"
ifschools = "source/ifschools.txt"
school_intro = "source/school_intro.txt"
school_cases = "source/school_cases.csv"
style_declaration = "source/style.txt"
creds = "creds/creds.ini"

###########################################
# Use care if adjusting values below here #
###########################################

#date/time info
rightnow = dt.datetime.today()
starttime = rightnow + dt.timedelta(days=1)
sy = starttime.strftime("%Y")
sm = starttime.strftime("%m")
sd = starttime.strftime("%d")
current = f"{sy}-{sm}-{sd}T00:00:00"

# vax date values - generally no need to adjust this unless you want a longer time interval
startdate = '2021-03-17T00:00:00'
enddate = current
age_ranges = ['5-11', '12-17', '18-24', '25-44', '45-64', '65+'] # do not adjust these values

#case values - generally no need to adjust this unless you want a longer time interval
startcase = '2021-03-17T00:00:00'
endcase = current

year = rightnow.strftime("%Y")
month = rightnow.strftime("%m")
day = rightnow.strftime("%d")
hour = rightnow.strftime("%H")
minute = rightnow.strftime("%M")

scan_datetime = f"{year}_{month}_{day}_{hour}_{minute}"
nowoclock = rightnow.strftime("%b %d, %Y")
run_time = f"This report was generated on {nowoclock} at {hour}:{minute}. "

x = len(town_list)
if x == 1:
	for t in town_list:
		alltowns = t
elif x == 2:
	alltowns = ""
	count = 0
	for t in town_list:
		count += 1
		if count < x:
			alltowns = alltowns + t + " and "
		if count == x:
			alltowns = alltowns + t
		else:
			pass
elif x > 2:
	alltowns = ""
	count = 0
	for t in town_list:
		count += 1
		if count < x:
			alltowns = alltowns + t + ", "
		if count == x:
			alltowns = alltowns + ", and " + t
		else:
			pass

title = f"Covid19 Vaccination Levels and Positive Cases in {alltowns}"
blog_title = f"Daily Summary for {alltowns}"
intro_text = '<p>This report uses data from the <a href="https://data.ct.gov/" alt="Open Data from the state of Connecticut" title="Open Data from the state of Connecticut">Connecticut Open Data Portal</a>. Data on <a href="https://data.ct.gov/Health-and-Human-Services/COVID-19-Vaccinations-by-Town-and-Age-Group/gngw-ukpw" alt="CT Data Portal data source" title="CT Data Portal data source">vaccination rates</a> are updated weekly; data on <a href="https://data.ct.gov/Health-and-Human-Services/COVID-19-Tests-Cases-and-Deaths-By-Town-/28fr-iqnx" alt="CT Data Portal data source" title="CT Data Portal data source">positive cases and deaths</a> are updated on weekdays (no weekends or holidays).</p>'
blog_source = intro_text
report_summary = intro_text + "<h3>Overview</h3>"

anchor_links = "<h3>Jump to detailed reports:</h3><ul>"
for t in town_list:
	named_anchor = ''.join(t.split()).lower()
	named_anchor_vax = f'"#{named_anchor}-vaccination"'
	named_anchor_cases = f'"#{named_anchor}-cases"'
	links = f'<li>{t}: <a href={named_anchor_cases}>Information about people contracting Covid;</a></li><li>{t}: <a href={named_anchor_vax}>Information about people getting vaccinated;</a></li>'
	anchor_links = anchor_links + links
if run_schools == "yes":
	anchor_links = anchor_links + f'<li><a href="#schools">Positive cases in schools.</a></a></li></ul>'
else:
	anchor_links = anchor_links + "</ul>"

# set ouput directories
report_dir = 'report/'

dir_list = [report_dir]
for d in dir_list:
	try:
		os.makedirs(d)
	except FileExistsError:
		pass

df_vax = pd.DataFrame(columns=['town', 'reported_date', 'age_group', 'initiated', 'vaccinated'])
df_cases = pd.DataFrame(columns=['town', 'date', 'total_cases', 'total_deaths'])
df_report = pd.DataFrame(columns=['town', 'text', 'sequence'])

# vax data source: https://data.ct.gov/Health-and-Human-Services/COVID-19-Vaccinations-by-Town-and-Age-Group/gngw-ukpw
# https://data.ct.gov/resource/gngw-ukpw.json?town=Lyme&$where=dateupdated between '2021-10-17T00:00:00' and '2021-11-24T00:00:00'
# populate vax dataframe with all data 
if run_vax == "yes":
	rdl = []
	enddate_str = enddate[:10]
	for t in town_list:
		print(f"Getting vaccination rate data for {t}\n")
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
#sort dates with most recent first
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
				'''
				if datefilter == str(vax_report_date_list[0])[:10]:
					if age_range == "5-11":
						initiated_05_11 = initiated
						vaccinated_05_11 = vaccinated
					elif age_range == "12-17":
						initiated_12_17 = initiated
						vaccinated_12_17 = vaccinated
					elif age_range == "18-24":
						initiated_18_24 = initiated
						vaccinated_18_24 = vaccinated
					elif age_range == "25-44":
						initiated_25_44 = initiated
						vaccinated_25_44 = vaccinated
					elif age_range == "45-64":
						initiated_45_64 = initiated
						vaccinated_45_64 = vaccinated
					elif age_range == "65+":
						initiated_65plus = initiated
						vaccinated_65plus = vaccinated
					else:
						pass
				'''
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

else:
	pass

# case data by source: https://data.ct.gov/Health-and-Human-Services/COVID-19-Tests-Cases-and-Deaths-By-Town-/28fr-iqnx
# https://data.ct.gov/resource/28fr-iqnx.json?town=Lyme&$where=lastupdatedate between '2021-10-30T00:00:00' and '2021-11-30T00:00:00'
# populate cases dataframe with all data
if run_cases == "yes":
	cdl = []
	endcase_str = endcase[:10]
	case_calcdate = datetime.strptime(endcase_str, '%Y-%m-%d')
	for t in town_list:
		print(f"Getting case and death rate data for {t}\n")
		case_url = f"https://data.ct.gov/resource/28fr-iqnx.json?town={t}&$where=lastupdatedate between '{startcase}' and '{endcase}'"
		case_data = json.loads(requests.get(case_url).text)
		past_case = 0
		past_death = 0
		for c in case_data:
			town = c['town']
			date = c['lastupdatedate'][:10]
			total_cases = c['towntotalcases']
			total_deaths = c['towntotaldeaths']
			case_obj = pd.Series([town, date, total_cases, total_deaths], index=df_cases.columns)
			df_cases = df_cases.append(case_obj, ignore_index=True)

# filter dataset by town and get counts
	blog_cases = ""
	for t in town_list:
		df_cases_filter = df_cases[(df_cases['town'] == t)]
		town_cases_text = ""
		# get dates of all reports in the dataset
		for a, b in df_cases_filter.iterrows():
			report_date = datetime.strptime(b['date'], '%Y-%m-%d')
			if report_date not in cdl:
				cdl.append(report_date)
		#sort dates with most recent first
		cdl.sort(reverse=True)
		case_report_date_list = cdl[:case_initial]
		startd = case_report_date_list[0]
		human_startd = startd.strftime("%b %d, %Y")
		endd = case_report_date_list[case_initial - 1]
		human_endd = endd.strftime("%b %d, %Y")
		difference = str((startd - endd)).split(',')
		named_anchor = ''.join(t.split()).lower()
		named_anchor = f'id="{named_anchor}-cases"'
		cases_header = f'\n<table {named_anchor}><tr class="cases"><th> Reported date </th><th> Total cases </th><th> Total deaths </th></tr>'
		casesline = ""
		for c in case_report_date_list:
			datefilter = str(c)[:10]
			df_cases_bytown = df_cases_filter[df_cases_filter['date'] == datefilter]
			for c,d in df_cases_bytown.iterrows():
				reporting_town = d['town']
				reported_date = d['date']
				positive_cases = d['total_cases']
				deaths = d['total_deaths']
				casesline = casesline + f"<tr><td>{reported_date}</td><td>{positive_cases}</td><td>{deaths}</td></tr>\n"
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
		day_rate = f"<h3>Positive Cases and Deaths in {t}</h3><ul><li>In the <b>{day_diff[0]}</b> between the two most recent reports on {human_startd} and {day_date}, <b>{ccl24} contracted Covid</b>, and <b>{dcl24} died</b> as a result of Covid.</li>"
		if case24 == 0 and death24 == 0:
			day_rate = f"<h3>Positive Cases and Deaths in {t}</h3><ul><li>In the <b>{day_diff[0]}</b> between the two most recent reports, no people have contracted Covid, or died as a result of Covid.</li>"
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

	run_time = run_time + f'The most recent data on cases and deaths included here is from <b>{human_startd}</b>. '
	blog_title = blog_title + " for " + human_startd
else:
	pass

## Schools
## This section is largely manual - blech
## Read in intro text from file
if run_schools == "yes":
	schools_text_header = '<h2 id="schools">Positive Cases in Schools</h2>'
	print(f"Processing school data.\n")
	with open(school_intro) as f:
		schools_text = f.read()

	with open(school_cases) as input:
		df_school_data = pd.read_csv(input)

	school_case_header = f'\n<table><tr class="cases"><th> Reported Date </th><th> Cases </th><th> School </th><th> Notes or Explanations </th></tr>'
	school_case_count = 0
	for r, s in df_school_data.iterrows():
		school_date = s['date']
		cases = s['cases']
		school_case_count = school_case_count + int(cases)
		school = s['school']
		notes = s['notes']
		if notes == "none":
			notes = ""
		else:
			pass
		school_line = f"<tr><td>{school_date}</td><td>{cases}</td><td>{school}</td><td>{notes}</td></tr>"
		school_case_header = school_case_header + school_line
	school_cases_text = f'<p>As of {human_startd}, the district superintendent has disclosed that <b>{str(school_case_count)} people in Lyme-Old Lyme Schools</b> have tested positive for Covid in the 2021-2022 school year.</p>'
	schools_full = schools_text_header + school_cases_text + schools_text + school_case_header + "</table>"
else:
	schools_full = ""

## Generate report
print(f"Generating an html report.\n")
## Using <style> in this way is Very Not Good
## These declarations should generally be in the head; because 
## this doesn't generate a head (or really a body either) I'm 
## throwing this in the body. It's janky but it works.
## I'd rather be done than proud.
with open(style_declaration) as f:
	style = f.read()

with open(opening) as f:
	intro_blurb = f.read()
report_summary = style + report_summary + intro_blurb

if run_schools == "yes":
	with open(ifschools) as f:
		school_blurb = f.read()
	report_summary = report_summary + school_blurb
else:
	pass

report_summary = report_summary + "<p>" + run_time + "</p>" + anchor_links + "\n<hr>"
df_report.sort_values(by=['sequence'], inplace=True)
all_text = ""
for t in town_list:
	df_report_filter = df_report[df_report['town'] == t]
	core_text = ""
	for p,q in df_report_filter.iterrows():
		core_text = core_text + q['text']
	named_anchor_town = ''.join(t.split()).lower()
	named_anchor_town = f'id="{named_anchor_town}"'
	all_text = all_text + "<h2 " + named_anchor_town + ">" + t + "</h2>" + core_text + "<hr>"
doc_text = report_summary + all_text + schools_full
htmlfile = scan_datetime + ".html"

with open(report_dir + htmlfile, 'w') as g:
	g.write(f"<h2>{title}</h2>{doc_text}")

if export_to_wordpress == "yes":
	print(f"Updating the site. This might take a minute.")
	#Read creds.ini file
	config = ConfigParser()
	config.read(creds)

	#Get options for details to include in summaries, and file format export options
	creds = config["WORDPRESS"]
	url_page = creds["url_page"]
	url_post = creds["url_post"]
	post_author = creds["post_author"]
	pageID = creds["pageID"]
	category = creds["categoryID"]
	user = creds["username"]
	password = creds["password"]

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
		print(f"\nThe page titled '{title}' updated sucessfully,\n")
	else: 
		print(f"There seems to be an issue with the update. This was the response code:\n{response}")

	blog_full_report = f'See the <a href="https://www.oldlymecovid.org/covid-case-rates-and-vaccination-information-for-lyme-and-old-lyme/" title="Full report of current data on Covid cases and vaccinations">detailed report of current information here</a>.'

	blog_content = style + run_time + blog_full_report + blog_cases + blog_vax_text + blog_source

	post = {
		'title':blog_title,
		'status': 'publish', 
		'content': blog_content,
		'categories':category,
		'author':post_author
		}

	response_post = requests.post(url_post, headers=header, json=post)
	if str(response_post) == "<Response [201]>":
		print(f"The blog post titled '{blog_title}' was created.\n")
	else: 
		print(f"There seems to be an issue with creating the post. This was the response code:\n{response_post}\nThis is the blog text:\n{blog_content}")

else:
	pass

print("Done!")