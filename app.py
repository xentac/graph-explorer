#!/usr/bin/env python2
import os, json, sys, traceback, re
from inspect import isclass
from bottle import route, run, debug, template, request, validate, static_file, redirect, response
from config import *

# this bit of code should be more dynamic but that goes beyond my python-fu
# we basically want to import all templates in a given directory, instantiate objects from their classes,
# and keep a list of all of them (pref. alphabetically ordered)
from graph_templates import GraphTemplate

template_objects = []
templates = []
modlist = ['cpu', 'swift_object_server', 'swift_tempauth']

for module in modlist:
    imp = __import__('graph_templates.'+module, globals(), locals(), ['*'])
    for itemname in dir(imp):
        item = getattr(imp, itemname)
        if isclass(item) and item != GraphTemplate and issubclass(item, GraphTemplate):
            template_objects.append(item())
            templates.append(module)

print "templates:", templates
print template_objects

def list_targets (metrics):
    targets = {}    
    for t_o in template_objects:
        targets.update(t_o.list_targets(metrics))
    return targets

def list_graphs (metrics):
    graphs = {}    
    for t_o in template_objects:
        graphs.update(t_o.list_graphs(metrics))
    return graphs

def parse_pattern(pattern):
    # if user specified "group by foobar" in the pattern, filter it out
    group_by_match = re.search('(group by [^ ]+)',pattern)
    group_by = None
    if group_by_match and group_by_match.groups() > 0:
        group_by = group_by_match.groups(1)[0].replace('group by ','')
        pattern = pattern[:group_by_match.start(1)] + pattern[group_by_match.end(1):]
    # split pattern into multiple words which are all matched independently
    # this allows you write words in any order, and also makes it easy to use negations
    pattern = pattern.split()
    # if the pattern doesn't contain a "graph type specifier" like 'tpl' or 'targets',
    # assume we only want tpl ones. that sounds like good default behavior..
    if 'tpl' not in pattern and 'targets' not in pattern:
        pattern.append('tpl')
    pattern = {
        'pattern': pattern,
        'group_by': group_by
    }
    return pattern

# objects is expected to be a dict with elements like id: data
# id's are matched, and the return value is a dict in the same format
# every part of the pattern must match
def match(objects, pattern):
    objects_matching = {}
    for (id, data) in objects.items():
        match = True
        for patt in pattern['pattern']:
            if patt.startswith('!'):
                if patt[1:] in id:
                    match = False
            else:
                if patt not in id:
                    match = False
        if match:
            objects_matching[id] = data
    return objects_matching

def load_metrics():
    f = open('metrics.json', 'r')
    return json.load(f)

@route('<path:re:/assets/.*>')
@route('<path:re:/graphitejs/.*js>')
@route('<path:re:/graphitejs/.*css>')
def static(path):
    return static_file(path, root='.')

@route('/', method='GET')
@route('/index', method='GET')
@route('/index/', method='GET')
@route('/index/<pattern>', method='GET')
def index(pattern = ''):
    output = template('page', body = template('body.index', pattern = pattern))
    return str(output)

@route('/index', method='POST')
def index_post():
    redirect('/index/%s' % request.forms.pattern)

@route('/debug')
def view_debug():
    metrics = load_metrics()
    targets = list_targets(metrics)
    graphs = list_graphs(metrics)
    graphs_targets, graphs_targets_options = build_graphs_from_targets(targets)
    args = {'templates': templates,
        'targets': targets,
        'graphs': graphs,
        'graphs_targets': graphs_targets,
        'graphs_targets_options': graphs_targets_options
    }
    output = template('page', page = 'debug', body = template('body.debug', args))
    return str(output)

@route('/debug/metrics')
def debug_metrics():
    response.content_type = 'text/plain'
    return "\n".join(load_metrics())

def build_graphs_from_targets(targets, options = {}):
    graphs = {}
    if not targets:
        return (graphs, options)
    # no group_by specified? pick most common default:
    # note that default_group_by is mandatory for each target
    if 'group_by' not in options or options['group_by'] is None:
        group_by_candidates = {}
        import operator
        for (id, data) in targets.items():
            group_by_candidates[data['default_group_by']] = group_by_candidates.get(data['default_group_by'],0) + 1
        sorted_candidates = sorted(group_by_candidates.iteritems(), key=operator.itemgetter(1), reverse = True)
        options['group_by'] = sorted_candidates[0][0]
    # for each occurence of the tag specified by group_by, make a graph (named after the value of this tag),
    # that gathers all targets which have this tag
    for target_id in sorted(targets.iterkeys()):
        target_data = targets[target_id]
        title = 'targets_' + target_data['tags'][options['group_by']]
        if title not in graphs:
            graphs[title] = {'title': title, 'targets': []}
        t = {
            'name': target_data['names'][options['group_by']],
            'target': target_data['target']
        }
        graphs[title]['targets'].append(t)
    return (graphs, options)

@route('/graphs/', method='POST')
@route('/graphs/<pattern>', method='GET') # used for manually testing
def graphs(pattern = ''):
    '''
    get all relevant graphs matching pattern,
    graphs yielded by templates directly,
    enriched by combining the yielded targets
    '''
    if not pattern:
        pattern = request.forms.get('pattern')
    metrics = load_metrics()
    targets_all = list_targets(metrics)
    graphs_all = list_graphs(metrics)
    pattern = parse_pattern(pattern)
    targets_matching = match(targets_all, pattern)
    graphs_matching = match(graphs_all, pattern)
    graphs_targets_matching = build_graphs_from_targets(targets_matching, pattern)[0]
    len_targets_matching = len(targets_matching)
    len_graphs_matching = len(graphs_matching)
    len_graphs_targets_matching = len(graphs_targets_matching)
    graphs_matching.update(graphs_targets_matching)
    len_graphs_matching_all = len(graphs_matching)
    out = ''
    if len_graphs_matching_all > 0 and request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        out += template('snippet.graph-deps')
    out += "Pattern: '%s'<br/>" % pattern['pattern']
    out += "# targets matching: %i/%i<br/>" % (len_targets_matching, len(targets_all))
    out += "# graphs matching: %i/%i<br/>" % (len_graphs_matching, len(graphs_all))
    out += "# graphs from matching targets: %i<br/>" % len_graphs_targets_matching
    out += "# total graphs: %i<br/>" % len_graphs_matching_all
    out += ''.join(template('snippet.graph', graphite_url = graphite_url, graph_name = title, graph_data = data) for (title, data) in graphs_matching.items())
    return out

debug(True)
run(reloader=True, host=listen_host)

# vim: ts=4 et sw=4:
