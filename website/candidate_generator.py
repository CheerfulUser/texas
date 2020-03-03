import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord

import pygsheets

from astropy.time import Time 

import warnings
warnings.filterwarnings("ignore")
import gspread
from oauth2client.service_account import ServiceAccountCredentials

def get_gglsheet():
# use creds to create a client to interact with the Google Drive API
    scope = ['https://spreadsheets.google.com/feeds',
		'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('client_secret.json', scope)
    client = gspread.authorize(creds)
    sheet = client.open("texas").sheet1
    return sheet

def Rise_covered(Table):
	"""
	Check to see if the rise of the transient is covered by TESS observations.

	Input:
	------
	Table - pandas dataframe 

	Outputs:
	--------
	ind 	- list, indicies that TESS covers
	sector 	- list, TESS sectors of the transients
	"""
	TESS_times = pd.read_csv('TESS_sector_jd.csv').values
	ind = []
	sector = []
	for i in range(len(Table)):
		maxtime = Time(Table['min_date'].iloc[i].replace(' ', 'T')).jd
		disc = Time(Table['disc_date'].iloc[i].replace(' ', 'T')).jd
		
		diff = maxtime - disc 
		if diff > 5:
			buffer = 20 # assuming max and rise is ~18 days
		else:
			buffer = 10 # arbitrary choice
		sneeze = ((TESS_times[:,1] < (maxtime - buffer)) & 
						  (TESS_times[:,2] > (maxtime - 3)))
		if sneeze.any():
			sector += [TESS_times[sneeze,0][0]]
			ind += [i]
	return ind, sector #Table[ind] 


def Check_gal_lat(Table):
	"""
	Calculates galactic latitude, which is used as a flag for event rates.
	"""
	ind = []
	for i in range(len(Table)):
		b = SkyCoord(ra=float(Table['transient_RA'][i])*u.degree, dec=float(Table['transient_Dec'][i])*u.degree, frame='icrs').galactic.b.degree
		if abs(b) >= 10:
			ind += [i]

	return ind

def Check_extinction(Table):
	ind = []
	for i in range(len(Table)):
		if Table['mw_ebv'][i] <= 0.2:
			ind += [i]
	return ind

def Check_point(Table):
	ind = []
	print(Table['point_source_probability'])
	for i in range(len(Table)):
		if np.isfinite(Table['point_source_probability'][i]) and Table['point_source_probability'][i] is not None:
			if Table['point_source_probability'][i] <= 0.8:
				ind += [i]
		else:
			ind += [i]
	return ind


def Gal_coord(Table):
	l = []
	b = []
	for i in range(len(Table)):
		c = SkyCoord(ra=float(Table['transient_RA'][i])*u.degree, dec=float(Table['transient_Dec'][i])*u.degree, frame='icrs')
		l += [c.galactic.l.degree]
		b += [c.galactic.b.degree]
	return l, b


def Check_type(Table):
	ind = np.where((Table['spec_class'] == 'SN Ia') | (Table['spec_class'] == 'None'))[0]
	return ind 

def Check_z(Table):
	return 0

def YSE_list():
	all_cand = pd.read_csv('https://ziggy.ucolick.org/yse/explorer/54/download?format=csv')
	all_cand = all_cand.drop_duplicates(subset='name')
	all_cand['spec_class'] = all_cand['spec_class'].fillna(value = 'None')
	# Spec tyoe 
	ind = Check_type(all_cand)
	good = all_cand.iloc[ind]
	good = good.reset_index(drop=True)
	# galactic latitude
	ind = Check_gal_lat(good)
	good = good.iloc[ind]
	good = good.reset_index(drop=True)
	# extinction
	ind = Check_extinction(good)
	good = good.iloc[ind]
	good = good.reset_index(drop=True)
	# point source
	ind = Check_point(good)
	good = good.iloc[ind]
	good = good.reset_index(drop=True)
	


	df = pd.DataFrame()
	#df['name'] = good['name'] + '#' + url + good['name'] + '/'
	links = []
	#for i in range(len(good['name'])):
	#	links += ['=HYPERLINK("https://ziggy.ucolick.org/yse/transient_detail/{0}/","{0}")'.format(good['name'].iloc[i])]
	l, b = Gal_coord(good)
	df['Name'] = good['name'] 
	df['RA'] = good['transient_RA']
	df['Dec'] = good['transient_Dec']
	df['l'] = l
	df['b'] = b
	df['Peak mag'] = good['min_mag']
	df['Peak time'] = good['min_date']
	df['Disc date'] = good['disc_date']
	df['Type'] = good['spec_class']
	ind = np.where(df['Type'].isna())[0]
	df['Type'].iloc[ind] = 'Phot ' + good['phot_class'].iloc[ind]
	df['PS prob'] = good['point_source_probability']
	ind2 = np.where(df['PS prob'].isna())[0]
	df['PS prob'].iloc[ind2] = 'None'
	df['Redshift'] = good['transient_z']
	ind3 = np.where(df['Redshift'].isna())[0]
	df['Redshift'].iloc[ind3] = 'None'
	df['MW E(B-V)'] = good['mw_ebv']
	
	return df


def Update_sheet():
	"""
	Updates the sheet.

	"""
#	filename = './candidates.csv'
#	web = pd.read_csv(filename)

	sheet = get_gglsheet()
	st_cont = sheet.get_all_values()
	headers = st_cont.pop(0)
	web = pd.DataFrame(st_cont, columns=headers)
	df = YSE_list()
#	print(web.keys())
	for i in range(len(df['Name'])):
		name = df['Name'][i]
		row = [df[col][i] for col in df.columns]
		if (web['Name'] == name).any():
			ind = int(np.where(web['Name'] == name)[0][0])+2
#			print('ind=', ind)
			sheet.delete_row(ind)
			sheet.insert_row(row, ind)
#			for col in df.columns:
#				web[col].iloc[ind] = df[col].iloc[i]
		else:
			print('Added ', name)
			sheet.insert_row(row, 2)
#			web.loc[-1] = df.iloc[i]
#			web.index = web.index + 1
#			web = web.sort_index()

#	web.iloc[:,15:] = web.iloc[:,10:].replace({pd.np.nan: ''})
	
#	web.to_csv(filename,index=False)
	print('Updated')
	return 

if __name__ == '__main__':
	Update_sheet()

