from . import site
from flask import render_template
import requests


@site.route('/')
@site.route('/<name>')
def home(name=None):
    provs = requests.get('http://localhost:5000/get_provinces')
    provs = provs.json()
    return render_template('home.html', name=name, provs=provs['data']['provinces'])


@site.route('/provinces', methods=['POST', 'GET'])
def provinces():
    provs = requests.get('http://localhost:5000/get_provinces')
    provs = provs.json()
    if provs['status'] == 'success':
        return render_template('provinces.html', provs=provs['data']['provinces'])
    else:
        return render_template('home.html', mess=provs['data'])


@site.route('/provinces/<province>/lines', methods=['POST', 'GET'])
def lines(province):
    lines = requests.get('http://localhost:5000/get_lines/{0}'.format(province))
    lines = lines.json()
    if lines['status'] == 'success':
        return render_template('lines.html', lines=lines['data']['lines'], prov=province)
    else:
        return render_template('home.html', mess=lines['data'])


@site.route('/provinces/<province>/lines/<line>', methods=['POST', 'GET'])
def only_line(province, line):
    return render_template('errors.html')


@site.route('/provinces/<province>/lines/<line>/to', methods=['POST', 'GET'])
def timetable_to(province, line):
    timetable = requests.get('http://localhost:5000/get_timetable/{0}/{1}/to'.format(province, line))
    timetable = timetable.json()
    # routes = requests.get('http://localhost:5000/get_routes/{0}'.format(timetable['data']['stops'])).json()
    # print(routes)
    if timetable['status'] == 'success':
        # print(timetable['data']['stops'])
        # print(timetable['data']['routes'])
        return render_template('onMap.html', times=timetable['data']['stops'], routes=timetable['data']['routes'])
    else:
        return render_template('errors.html', mess=timetable['message'])


@site.route('/provinces/<province>/lines/<line>/from', methods=['POST', 'GET'])
def timetable_from(province, line):
    timetable = requests.get('http://localhost:5000/get_timetable/{0}/{1}/from'.format(province, line))
    timetable = timetable.json()
    # routes = requests.get('http://localhost:5000/get_routes/{0}'.format(timetable['data']['stops'])).json()
    # print(routes)
    if timetable['status'] == 'success':
        # print(timetable['data']['stops'])
        # print(timetable['data']['routes'])
        return render_template('onMap.html', times=timetable['data']['stops'], routes=timetable['data']['routes'])
    else:
        return render_template('errors.html', mess=timetable['message'])
