#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Simple Bot to reply to Telegram messages
# This program is dedicated to the public domain under the CC0 license.
"""
This Bot uses the Updater class to handle the bot.

First, a few callback functions are defined. Then, those functions are passed to
the Dispatcher and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.

Usage:
Example of a bot-user conversation using ConversationHandler.
Send /start to initiate the conversation.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

from telegram import ReplyKeyboardMarkup
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, RegexHandler,
                          ConversationHandler)

import logging

import sqlite3, sys, urllib
import xml.etree.ElementTree as etree
from lxml import html, etree
import requests
from time import localtime, strftime
#from lxml import etree
import datetime
from bs4 import BeautifulSoup
from unidecode import unidecode
import distance
# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

CHOOSING, LUGAR = range(2)

reply_keyboard = [['Aemet por días', 'Aemet por horas'],
#                  [, 'eltiempo.es por horas'],
				  ['Ubicación', 'Unidades'],]
markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)

url_aemet_dias='http://www.aemet.es/xml/municipios/localidad_%s.xml'
url_aemet_general='http://www.aemet.es/es/eltiempo/prediccion/municipios/%s-id%s'
url_aemet_horas='http://www.aemet.es/xml/municipios_h/localidad_h_%s.xml'
url_eltiempo_dias='https://www.eltiempo.es/%s.html'
url_eltiempo_horas='https://www.eltiempo.es/%s.html?v=por_hora'

conn = sqlite3.connect('aemet.db') #database with location codes for Aemet website
c= conn.cursor()

cod = {} #global variable for storing each users' location code
place = {} #global variable for storing each users' location

def start(bot, update):
	update.message.reply_text("¡Hola! Soy un bot del tiempo. Indícamen una ubicación y consultaré la previsión meteorológica")
	return LUGAR


def elegir(bot, update, user_data):
    update.message.reply_text('¿En qué sitio quieres conocer el tiempo?')
    return LUGAR

	
def ubica(bot, update, user_data):
	conn = sqlite3.connect('aemet.db')
	c= conn.cursor()
	sitio = update.message.text.title()
	c.execute('SELECT * FROM municipio WHERE nombre=?', (sitio,))
	base=c.fetchone()
	if base is None :
		update.message.reply_text('Parece que no está bien escrito, déjame ver...')
		c.execute('SELECT * FROM municipio')
		flag=0
		i=0
	
		while i< 9208:
			base=c.fetchone()
			if distance.levenshtein(unidecode(sitio.lower()), unidecode(base[0].lower()), normalized=True)<0.2:
				flag=1
				break
			i+=1
		if flag ==0:
			update.message.reply_text('Ubicación no encontrada. Por favor, indica el municipio que quieres buscar:')
			return LUGAR
	
	cod[update.message.chat.id]=base[1]

	update.message.reply_text("Se ha elegido el municipio %s, en %s" % (base[0], base[2]), reply_markup=markup)
	place[update.message.chat.id]=base[1]

	return CHOOSING	

def cota_nieve(tree,a,b):
	if 	tree[4][a][b].text != None :
		return ('\nCota de nieve: %sm' % (str(tree[4][a][b].text)))
	else:
		return ('')

def alerta(bloque):
	un=list(bloque.children)
	d=1
	texto=''
	while d<len(un) :
		dos=str(un[d])
		tres=dos[15:dos.find('class="margin')-2]
		if tres != 'Sin Riesgo' :
			texto+=('\n%s' % (tres))
		d+=2
	return texto	

def conecta_web(current_url):
	try: 
		response = requests.get(current_url)
	except:
		update.message.reply_text("La página web no responde", reply_markup=markup)
		return CHOOSING
		
	data= response.content
	response.close()
	return data
	
def cabecera(tree):
	return ('Elaborado: %s %s \n%s, %s' % (str(tree[1].text)[:10], str(tree[1].text)[11:], tree[2].text ,tree[3].text))
	
def ae_diario(bot, update, user_data):
	#hora=int(strftime("%H", localtime()))

	current_url = url_aemet_dias % cod[update.message.chat.id]
	data=conecta_web(current_url)
	tree = etree.fromstring(data)

	current_url = url_aemet_general % (unidecode(tree[2].text.replace(' ','-').lower()), cod[update.message.chat.id])
	data=conecta_web(current_url)
	soup = BeautifulSoup(data, 'html.parser')
	por_dias=soup.find_all(class_='comunes alinear_texto_centro')
	hora=int(str(tree[1].text)[11:13])	
	if hora<=5:
		a=0;
	elif hora<=11:
		a=1;
	elif hora<=17:
		a=2;
	else :
		a=3;
	
	hora=int(strftime("%H", localtime()))
	if hora<=5:
		j=0-a;
	elif hora<=11:
		j=1-a;
	elif hora<=17:
		j=2-a;
	else :
		j=3-a;
				
#	texto=('Elaborado: %s %s' % (str(tree[1].text)[:10], str(tree[1].text)[11:]))
#	texto+=('\n%s, %s' % (tree[2].text ,tree[3].text))
	
	texto=cabecera(tree)
	texto+=('\n%s  UV:%s  %s' % (str(tree[4][0].attrib)[11:21] ,tree[4][0][38].text, str(tree[4][0][15+int(a/2)].attrib)[37:-2]))
	
	texto+=alerta(por_dias[0])

	texto+=cota_nieve(tree,0,7)
	
	a+=j
	
	while a<=7:
		b=int(a//4)
		c=a%4
		
		if a == 4:
			texto+=('\n\n%s  UV:%s  %s' % (str(tree[4][1].attrib)[11:21] ,tree[4][1][38].text, str(tree[4][1][14].attrib)[37:-2]))
			
			texto+=alerta(por_dias[1])

			texto+=cota_nieve(tree,1,7)
			
			#j=0
		
		texto+=('\n%sh: %sºC (%s) %s%% %s %skm/h' % (str((tree[4][0+b][3+c].attrib))[13:18], tree[4][0+b][35][2+c].text, tree[4][0+b][36][2+c].text, tree[4][0+b][3+c].text, tree[4][0+b][24+c][0].text, tree[4][0+b][24+c][1].text))
		#texto+=('\n%d %d %d %d' % (a, b, c, j))
		
		#texto+=('\n%sh:  ' % (str((tree[4][0+b][3+c].attrib))[13:18]))#, tree[4][0+b][35][2+c+j].text))#, tree[4][0+b][36][2+c+j].text, tree[4][0+b][3+c+j].text, tree[4][0+b][24+c+j][0].text, tree[4][0+b][24+c+j][1].text))
		a=a+1

	a=0
	b=0
	while a<=1:
		texto+=('\n\n%s  UV:%s  %s' % (str(tree[4][2+a].attrib)[11:21], tree[4][2+a][18].text, str(tree[4][2+a][6].attrib)[37:-2]))
	
		texto+=alerta(por_dias[2])
		texto+=cota_nieve(tree,2,3)
		texto+=('\n%sºC (%s)  / %sºC (%s)' % (tree[4][2+a][15][1].text, tree[4][2+a][16][1].text, tree[4][2+a][15][0].text, tree[4][2+a][16][0].text))
		while b<=1:
			texto+=('\n%sh: %s%%  %s %s km/h' % (str((tree[4][2][1+b].attrib))[13:18], tree[4][2+a][1+b].text, tree[4][2+a][10+b][0].text, tree[4][2+a][10+b][1].text))
			b+=1
		a+=1
		b=0
	a=0
	while a<=2:
		texto+=('\n\n%s %s' % (str(tree[4][4+a].attrib)[11:21], str(tree[4][4+a][2].attrib)[17:-2]))
		texto+=('\n%sºC (%s)/ %sºC (%s) %s%% %s %skm/h' % (tree[4][4+a][5][1].text, tree[4][4+a][6][1].text, tree[4][4+a][5][0].text, tree[4][4+a][6][0].text, tree[4][4+a][0].text, tree[4][4+a][3][0].text, tree[4][4+a][3][1].text))	
		a=a+1

	update.message.reply_text(texto, reply_markup=markup)
	return CHOOSING		

def ae_horario(bot, update, user_data):
	current_url = url_aemet_horas % cod[update.message.chat.id]
	data=conecta_web(current_url)
	tree = etree.fromstring(data)
	
	texto=cabecera(tree)

#	texto=('Elaborado: %s %s' % (str(tree[1].text)[:10], str(tree[1].text)[11:]))
#	texto+=('\n%s, %s' % (tree[2].text ,tree[3].text))

	hora_prediccion=int(str(tree[1].text)[11:13])
	
	q1=1+localtime()[8] #Daylight saving period changes xml structure
	q2=7+localtime()[8]
	q3=13+localtime()[8]
	q4=19+localtime()[8]
	
	if hora_prediccion<q1:
		a=0;
	elif hora_prediccion<q2:
		a=q1;
	elif hora_prediccion<q3:
		a=q2;
	else :
	#elif hora_prediccion<q4:
		a=q3;
	#else :
	#	a=q4	

	#b=parte#+1-localtime()[8]
	b=int(strftime("%H", localtime()))
	c=24-a	
	if hora_prediccion < b :
		while b<24:
			#kk=('%d %d %d' %(a, b, c))
			#update.message.reply_text(kk+texto, reply_markup=markup)

			texto+=('\n%sh:  %sºC  (%s)  %smm  %s %skm/h' % (str(tree[4][0][b-a].attrib)[13:15], tree[4][0][84+b-4*a].text, tree[4][0][108+b-5*a].text, tree[4][0][24+b-2*a].text, tree[4][0][156+2*b-8*a][0].text, tree[4][0][156+2*b-8*a][1].text))
			if tree[4][0][56+b-3*a].text != '0':
				texto+=('\t *%s' % tree[4][0][56+b-3*a].text)
			b+=1
		b=0	
	
	#b=0
	while b<24:
		#kk=('%d %d %d' %(a, b, c))
		#update.message.reply_text(kk+texto, reply_markup=markup)

		texto+=('\n%sh:  %sºC  (%s)  %smm  %s %skm/h' % (str(tree[4][1][b].attrib)[13:15], tree[4][1][84+b].text, tree[4][1][108+b].text, tree[4][1][24+b].text, tree[4][1][156+2*b][0].text, tree[4][1][156+2*b][1].text))
		if tree[4][1][56+b].text != '0':
			texto+=('\t *%s' % tree[4][1][56+b].text)
		b+=1
	b=0
	while b<a:
		#kk=('%d %d %d' %(a, b, c))
		#update.message.reply_text(kk, reply_markup=markup)

		texto+=('\n%sh:  %sºC  (%s)  %smm  %s %skm/h' % (str(tree[4][2][b].attrib)[13:15], tree[4][2][84+b-3*c].text, tree[4][2][108+b-4*c].text, tree[4][2][24+b-c].text, tree[4][2][156+2*b-6*c][0].text, tree[4][2][156+2*b-6*c][1].text))
		if tree[4][2][56+b-2*c].text != '0':
			texto+=('\t *%s' % tree[4][2][56+b-2*c].text)
		b+=1
	update.message.reply_text(texto, reply_markup=markup)
	return CHOOSING	

# def et_diario(bot, update, user_data):
	# current_url = url_eltiempo_dias % place[update.message.chat.id]
	# data=conecta_web(current_url)
	# soup = BeautifulSoup(data, 'html.parser')
	# por_dias=soup.find_all(class_='m_table_weather_day_temp_wrapper')
	# bloque=str(por_dias[7])
	
	# texto=''
	
	# texto+=('Elaborado: %s %s\n' % (datetime.date.today(), soup.find(class_="m_city_lastupdate_time").get_text()))
	# texto+=('%s, %s\n' %(place[update.message.chat.id], cod[update.message.chat.id] ))
	
	# a=0
	# while a<=20 :
		# if ((a%3)==0) :
			# texto+=('%s %s\n' % (datetime.date.today() + datetime.timedelta(days=int(a//3)) , bloque[bloque.find('popup_forecast')+16:bloque.find('popup_icon')-2] ))
			# texto+=('8h: ')
		
		# if ((a%3)==1) :
			# texto+=('14h:')
		
		# if ((a%3)==2) :
			# texto+=('20h:')

		# texto+=(' %s (%s) %s%% %s\n' %(bloque[bloque.find('popup_temp_orig')+17:bloque.find('popup_wind')-2], bloque[bloque.find('popup_feels_like_orig')+23:bloque.find('popup_feels_like_text')-2], bloque[bloque.find('popup_prob_rain_orig')+22:bloque.find('popup_prob_rain_text')-2], bloque[bloque.find('popup_wind_orig')+17:bloque.find('popup_wind_orig')+19]))

		# if ((a%3)==2) :
			# texto+=('\n')
		# a+=1
		# bloque=str(por_dias[7+a])
	# update.message.reply_text(texto, reply_markup=markup)
	# return CHOOSING

# def et_horario(bot, update, user_data):
	# current_url = url_eltiempo_horas % place[update.message.chat.id]
	# data=conecta_web(current_url)
	# update.message.reply_text('Esto tardará un poco')
	# soup = BeautifulSoup(data, 'html.parser')
	# por_horas=soup.find_all(class_='m_table_weather_day_temp_wrapper')
	# #bloque=por_horas[1]

	# texto=('Elaborado: %s %s\n' % (datetime.date.today(), soup.find(class_="m_city_lastupdate_time").get_text()))
	# texto+=('%s, %s\n' %(place[update.message.chat.id], cod[update.message.chat.id] ))
	
	# a=0
	# #b=0

	# while a<=49 :
		# por_horas=soup.find_all(class_='m_table_weather_hour_detail_hours')
		# hora=(str(por_horas[1+a])[47:-9])
		# texto+=('%sh: ' % (hora))
		
		# por_horas=soup.find_all(class_='m_table_weather_hour_detail_pred')
		# un=por_horas[1+a]
		# dos=list(un.children)[0]
		# tres=list(dos.children)
		# texto+=('%s ' % (str(tres)[2:-3]))
		
		# #por_horas=soup.find_all(class_='m_table_weather_hour_detail_child')
		# #un=por_horas[2+b]
		# #dos=str(list(un.children)[3])
		# #texto+=('(%s) ' % (dos[23:dos.find('data-temp-include-units')-2]))
		
		# por_horas=soup.find_all(class_='m_table_weather_hour_detail_rain m_table_weather_hour_detail_child_mobile')
		# texto+=('%smm ' % (str(por_horas[1+a])[156:-17]))
		
		# por_horas=soup.find_all(class_='m_table_weather_hour_detail_med')
		# un=str(por_horas[1+a])
		# texto+=('%s \n' % (un[62:un.find('data-wind-include-units')-2]))
		
		# a+=1
		# #if b<42 :
		# #	b+=3
		# #else :
		# #	b+=2
			
		# if hora == '23' :
			# a+=1


	# update.message.reply_text(texto, reply_markup=markup)
	# #update.message.reply_text('Es muy probable que haya valores que no han salido bien. Lo cierto es que la web eltiempo.es no es muy consistente en su forma de dar los datos, y resulta algo complejo obtenerlos (por eso es lento)', reply_markup=markup)
	# return CHOOSING

def unid(bot, update, user_data):
	text = update.message.text
	user_data['choice'] = text
	texto=('Parte diario:\n T [ºC] (Sens térmica [ºC]) Prob lluvia Dir + Fuerza viento [km/h]\n')
	texto+=('T min [ºC] (Sens térm min [ºC])/ T max [ºC] (Sens térm max [ºC]) Prob lluvia Dir + Fuerza viento [km/h]\n')
	texto+=('Parte horario:\n T [ºC] (Sens térm [ºC]) Lluvia [mm] Dir + Fuerza viento [km/h]\n')
	update.message.reply_text(texto, reply_markup=markup)
	return CHOOSING


def done(bot, update, user_data):
    if 'choice' in user_data:
        del user_data['choice']

    update.message.reply_text("I learned these facts about you:")

    user_data.clear()
    return ConversationHandler.END


def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))


def main():
    # Create the Updater and pass it your bot's token.
    updater = Updater("TOKEN")

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Add conversation handler with the states GENDER, PHOTO, LOCATION and BIO
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],

        states={
            CHOOSING: [RegexHandler('^(Aemet por días)$',
                                    ae_diario,
                                    pass_user_data=True),
                       RegexHandler('^(Aemet por horas)$',
									ae_horario,
                                    pass_user_data=True),
			           # RegexHandler('^(eltiempo.es por días)$',
									# et_diario,
                                    # pass_user_data=True),
                       # RegexHandler('^(eltiempo.es por horas)$',
									# et_horario,
                                    # pass_user_data=True),
                       RegexHandler('^(Ubicación)$',
									elegir,
                                    pass_user_data=True),
                       RegexHandler('^(Unidades)$',
									unid,
                                    pass_user_data=True),									
									],
					   
            LUGAR: [MessageHandler(Filters.text,
                                          ubica,
                                          pass_user_data=True),
                           ],

        },

        fallbacks=[RegexHandler('^Done$', done, pass_user_data=True)]
    )

    dp.add_handler(conv_handler)

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
	