# Human Readable Reports from Connecticut Covid Data

This script pulls data from the [Connecticut Open Data Portal](https://data.ct.gov/browse?tags=covid-19) and generates human-readable reports.

The reports are minimal by design, and include a quick snapshot of positive cases and vaccination levels in specific towns, alongside a more detailed report that contains more data over time.

The script can pull data from any town in the dataset, and the time interval covered by the reports is also configurable.

The script also includes an option to export the reports (a daily summary blog post and the more detailed report) into a Wordpress site. To see a working site with this functionality in action:

* [Daily Snapshots](https://www.oldlymecovid.org/category/daily-snapshot/)
* [Detailed Report](https://www.oldlymecovid.org/covid-case-rates-and-vaccination-information-for-lyme-and-old-lyme/)

Exporting to Wordpress is optional, and this feature can be disabled via a toggle (**export_to_wordpress = "no"**) in the script.

# Setting up Export to Wordpress

You don't need to use Wordpress to use this script. If you do, these steps will be useful.

If you want to export reports into Wordpress, I recommend installing the [Classic Editor](https://wordpress.org/plugins/classic-editor/) plug in. This allows for cleaner handling of html on import.

Create a user account for the author that will be publishing. In the profile of the account, set an "Application Password". This password should be entered in the **creds.ini** in the **creds** directory. You will need to create both the directory and the file, and to state the obvious this file should never be shared. This repository contains a sample creds.ini file you can adapt.

# Caveats and disclaimers

This script works, but that is not the same as it being good. This script contains multiple hacks; I'm not a developer, and any code I write shows that very clearly. About the only good thing I can say about this code is that it works.

Pull requests and improvements are welcome. 

