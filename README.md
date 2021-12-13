# Human Readable Reports from Connecticut Covid Data

This script pulls data from the [Connecticut Open Data Portal](https://data.ct.gov/browse?tags=covid-19) and generates human-readable reports.

The script can be configured to generate reports on one or more towns; for each town, the report contains the town population, percentages of people vaccinated by age group, new positive cases, and new deaths.

Optionally, the script will generate a summary blog post that can be posted automatically to any Wordpress-based site.

This screencast gives an overview on how to use the script:

<div style="padding:75% 0 0 0;position:relative;"><iframe src="https://player.vimeo.com/video/656112279?h=a0eac9978e&amp;badge=0&amp;autopause=0&amp;player_id=0&amp;app_id=58479" frameborder="0" allow="autoplay; fullscreen; picture-in-picture" allowfullscreen style="position:absolute;top:0;left:0;width:100%;height:100%;" title="covid_data.mp4"></iframe></div><script src="https://player.vimeo.com/api/player.js"></script>

The reports are minimal by design. If you are reading this and have an idea on details that would be helpful to add, please let me know by [opening an issue](https://github.com/billfitzgerald/ct_covid_data/issues/new).

To see a working site using this script:

* [Daily Snapshots](https://www.oldlymecovid.org/category/lyme-old-lyme-daily-snapshot/)
* [Detailed Report](https://www.oldlymecovid.org/covid-case-rates-and-vaccination-information-for-lyme-and-old-lyme/)

## Config Options

The script is fairly flexible. The core settings are defined in json files in the **batches** directory. The most important settings in the file are the **batch_name** and the **town_list** settings. 

The **run_schools** option should be left to "no" unless you have a source of data for schools; the script offers some options for importing school data, but given the lack of standard data sources about schools, this is largely a custom process.

## Importing County-level data from the CDC

To provide more context around town-level data, the script now supports getting county-level data from the CDC. These data are updated daily on weekdays, and help flesh out what is happening in a geographic area.

![Import CDC data](https://github.com/billfitzgerald/ct_covid_data/blob/main/images/county_data.png "Set the values to import CDC data")

To import data from the CDC, you need to set the **run_cdc** option to "yes", and then enter the [FIPS code](https://en.wikipedia.org/wiki/Federal_Information_Processing_Standard_state_code) (or codes) in the batches .json file.

## Setting up Export to Wordpress

You don't need to use Wordpress to use this script. If you want to export to Wordpress: 

First, set the **export_to_wordpress** toggle to "yes".

Then, set up a page in your Wordpress site to hold the detailed report, and a post category for your posts.

If you want to export reports into Wordpress, I recommend installing the [Classic Editor](https://wordpress.org/plugins/classic-editor/) plug in. This allows for cleaner handling of html on import.

Create a user account for the author that will be publishing. In the profile of the account, set an "Application Password". This password should be entered in the **creds.ini** in the **creds** directory. You will need to create both the directory and the file, and to state the obvious this file should never be shared. This repository contains a sample creds.ini file you can adapt.

TODO: create screencast that documents the script and the setup.

## Caveats and disclaimers

This script works, but that is not the same as it being good. This script contains multiple hacks; I'm not a developer, and any code I write shows that very clearly. About the only good thing I can say about this code is that it works.

Pull requests and improvements are welcome. 

