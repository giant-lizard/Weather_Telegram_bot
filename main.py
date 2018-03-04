#!/usr/bin/python
# -*- coding: utf-8 -*-

from lxml import etree
import time, sqlite3, urllib
import requests


id = 1
i = 1001
fin = 52002
url = 'http://www.aemet.es/xml/municipios/localidad_%s.xml'
delay = 0.5
count=0
conn = sqlite3.connect('aemet2.db')
cursor = conn.cursor()
query = 'INSERT INTO municipio VALUES ("%s", "%s", "%s");'
cursor.execute('''CREATE TABLE municipio (nombre, codigo, provincia)''')
#log = file('log.txt', 'w+')

while i <= fin:
	cod = str(i)
	id=int(i//1000)
	if len(cod) < 5:
		cod = '0' + cod
	current_url = url % cod
	response = requests.get(current_url)

	print('%s %s %s' % (i, id, response.status_code))

	if response.status_code == 404 :
		time.sleep(delay)
		i += 1
		count+=1
		if (((i%1000)>490) & (count>100)):
			i=(i//1000)*1000+900
			count=0
		continue
		
	xml = etree.fromstring(response.content)
	response.close()
				
	nombre_municipio = str(xml.xpath('//nombre')[0].text)
	nombre_provincia = str(xml.xpath('//provincia')[0].text)
	
	print('%s %s %s %s' %(i, nombre_municipio, cod, nombre_provincia))
	
	largo = len(nombre_municipio)
	a=0
	while a< largo:
		if ((nombre_municipio[a] == '-') | (nombre_municipio[a] == '/')) :
			current_query = query % (nombre_municipio[:a], cod, nombre_provincia)
			cursor.execute(current_query)
			conn.commit()
			#log.write('Added. %s ' % cod)
			current_query = query % (nombre_municipio[a+1:], cod, nombre_provincia)
			cursor.execute(current_query)
			conn.commit()
			#log.write('Added. %s ' % cod)
		
		if (nombre_municipio[a] == ','):
			current_query = query % ((nombre_municipio[a+1:]+' '+nombre_municipio[:a]), cod, nombre_provincia)
			cursor.execute(current_query)
			conn.commit()			
		a+=1	
			
	current_query = query % (nombre_municipio, cod, nombre_provincia)
	try:
		cursor.execute(current_query)
		conn.commit()
		#log.write('Added. %s ' % cod)
	except:
		#log.write('Error executing: %s \n' % current_query.encode('utf-8') )
		pass
	#except: # urllib.HTTPError:
	#	pass
	time.sleep(delay)
	i += 1
#log.close()
conn.close()

