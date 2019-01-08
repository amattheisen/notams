wget -O todays_notams.html 'https://pilotweb.nas.faa.gov/PilotWeb/noticesAction.do?queryType=ALLGPS&formatType=DOMESTIC'
grep '!GPS' todays_notams.html
