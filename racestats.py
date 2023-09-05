#!/usr/bin/env python3

cbftp_api = '127.0.0.1:55477'
api_password = 'your_api_password'

import json
import os
import ssl
import sys
import urllib3
from operator import itemgetter
def req(path):
  http = urllib3.PoolManager(cert_reqs=ssl.CERT_NONE)
  headers = urllib3.make_headers(basic_auth=':%s' % api_password)
  r = http.request('GET', 'https://%s/%s' % (cbftp_api, path),
    headers=headers)
  if r.status >= 400:
    if r.status == 401:
      print('Error: invalid API password')
    elif r.status == 404:
      print('Error: path not found: ' + path)
    else:
      print('Error: Received HTTP status %s for %s' % (r.status, path))
    sys.exit(1)
  if len(r.data) == 0:
    return {}
  return json.loads(r.data)
def compare_size(user1, user2):
  return user1['bytes'] > user2['bytes']
def size_in_mb(bytes):
  mb = float(bytes) / 1024 / 1024
  return '%.1fMB' % mb
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
if len(sys.argv) < 3:
    print('Usage: ' + sys.argv[0] + ' <site> <spreadjob_or_path>')
    sys.exit(0)
site_name = sys.argv[1]
release = sys.argv[2]
site = req('sites/' + site_name)
if (release.startswith('/')):
  release_path = release
  release_name = os.path.basename(release_path)
else:
  spreadjob = req('spreadjobs/' + release)
  section = spreadjob['section']
  site_sections = site['sections']
  section_path = None
  for site_section in site_sections:
    if site_section['name'] == section:
      section_path = site_section['path']
      break
  if not section_path:
    print('Error: section %s does not exist on %s' % (section, site_name))
    sys.exit(1)
  release_path = section_path + '/' + release
  release_name = release
filelist = req('filelist?site=%s&path=%s' % (site_name, release_path))
stats = {}
for file in filelist:
  if file['type'] != 'FILE':
    continue
  user = file['user'] + '/' + file['group']
  if user not in stats:
    stats[user] = {'files': 0, 'bytes': 0}
  stats[user]['files'] += 1
  stats[user]['bytes'] += file['size']
stats_list = []
longest_username = 0
longest_filecount = 0
longest_total_size_mb = 0
total_files = 0
total_bytes = 0
for user in stats:
  user_stats = stats[user]
  files = user_stats['files']
  bytes = user_stats['bytes']
  stats_list.append({'user': user, 'files': files, 'bytes': bytes})
  total_bytes += bytes
  total_files += files
  if len(user) > longest_username:
    longest_username = len(user)
  if len(str(files)) > longest_filecount:
    longest_filecount = len(str(files))
  if len(size_in_mb(bytes)) > longest_total_size_mb:
    longest_total_size_mb = len(size_in_mb(bytes))
sorted_stats = sorted(stats_list, key=itemgetter('bytes'), reverse=True)
position = 1
print('%s  %sF  %s' % (release_name, total_files, size_in_mb(total_bytes)))
for user_stat in sorted_stats:
  user = user_stat['user']
  files = user_stat['files']
  bytes = user_stat['bytes']
  percentage = 100 * bytes / total_bytes
  file_count_len = longest_username - len(user) + longest_filecount + 1
  print ('%*s %s %*sf  %*s  %*.1f%%' % (2, position, user, file_count_len,
    files, longest_total_size_mb, size_in_mb(bytes), 4, percentage))
  position += 1
