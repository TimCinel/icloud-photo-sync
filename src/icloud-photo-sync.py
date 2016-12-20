#!/usr/bin/env python

import os
import time
import datetime
import argparse
import logging
import shutil

import yaml
from pyicloud import PyiCloudService
from hachoir_core.error import HachoirError
from hachoir_core.stream import InputIOStream
from hachoir_parser import guessParser
from hachoir_metadata import extractMetadata

def get_creation_date_from_metadata(media_file):
  with open(media_file) as f:
    f.seek(0)

    parser = guessParser(InputIOStream(f, None, tags=[]))
    metadata = extractMetadata(parser)

    return time.mktime(metadata.get('creation_date').timetuple())

def icloud_photo_sync(username, password, dest_dir=os.getcwd(), skip_exists=True, link_dir=None, purge=False):
  logging.info("logging in...")
  api = PyiCloudService(username, password)

  logging.info("calling update...")
  api.photos.albums['All Photos']
  api.photos.update()

  logging.info("getting photos...")
  stack = []
  for photo in api.photos.albums['All Photos']:
    stack.append(photo)
  stack.sort(key=lambda x: x.created, reverse=True)

  num_purge = 0
  num_skip = 0
  num_download = 0
  num_link = 0
  num_copy = 0

  # purge
  if purge:
    for existing_file in os.listdir(dest_dir):
      if existing_file[0:1] == ".":
        continue
      existing_file_path = os.path.join(dest_dir, existing_file)
      logging.debug("considering purge of %s" % existing_file_path)
      if os.path.isfile(existing_file_path) and len(filter(lambda photo: photo.filename == existing_file, stack)) == 0:
        logging.info("purging %s" % existing_file_path)
        try:
          os.remove(existing_file_path)
          num_purge = num_purge + 1
        except:
          logging.error("failed to purge %s" % existing_file_path)


  # download
  for photo in stack:
    photo_file = os.path.join(dest_dir, photo.filename)

    # skip if exists
    if os.path.isfile(photo_file) and skip_exists:
      logging.debug("skipped %s" % photo_file)
      num_skip = num_skip + 1
      continue

    # download
    with open(photo_file, 'wb') as f:
      logging.info("downloading %s" % photo_file)
      try:
        f.write(photo.download().raw.read())
        num_download = num_download + 1
      except Exception as e:
        logging.info("Error while downloading, cleaning up. Error: %s", e.message)
        f.close()
        os.remove(photo_file)
        raise Exception()

    ## update modified time
    try:
      # try to fetch from JPEG, PNG or MOV metadata
      modified_time = get_creation_date_from_metadata(photo_file)
    except:
      # use iCloud upload time (sadness, tears)
      modified_time = time.mktime(datetime.datetime.strptime(stack[0].created, "%Y-%m-%dT%H:%M:%SZ").timetuple())

    os.utime(photo_file, (modified_time, modified_time))

    # hard link
    if link_dir is not None:
      link_file = os.path.join(link_dir, photo.filename)

      if not os.path.isfile(link_file):
        try:
          os.link(photo_file, link_file)
          logging.info("linked %s" % photo_file)
          num_link = num_link + 1
        except:
          try:
            shutil.copy2(photo_file, link_file)
            num_copy = num_copy + 1
            logging.info("copied %s (link failed)" % photo_file)
          except Exception as e:
            logging.error("failed to link then failed to copy %s: %s", photo_file, e.message)
      else:
        logging.debug("already linked %s" % photo_file)
    else:
      logging.debug("skipping link")

  logging.info("Finished. Report:\n")
  logging.info(
      "\tdownloaded: %d\n\tskipped:%d\n\tpurged: %d\n\tlinked: %d\n\tcopied: %d",
      num_download, num_skip, num_purge, num_link, num_copy)

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('-u', '--username', default=None)
  parser.add_argument('-p', '--password', default=None)
  parser.add_argument('-c', '--creds-file', default=None)
  parser.add_argument('-d', '--download-dir', default=None)
  parser.add_argument('-l', '--link-dir', default=None)
  parser.add_argument('-s', '--skip-exists', default=False, action='store_true')
  parser.add_argument('-r', '--remove-missing', default=False, action='store_true')
  parser.add_argument('-v', '--verbose', default=False, action='store_true')
  args = parser.parse_args()

  if args.verbose:
    logging.basicConfig(level=logging.DEBUG)
  else:
    logging.basicConfig(level=logging.INFO)

  if args.creds_file is not None:
    with open(args.creds_file) as f:
        creds = yaml.load(f)
        username = creds['username']
        password = creds['password']
    try:
      pass
    except:
      raise ValueError("Failed to load creds from file")
  elif args.username is None or args.password is None:
    raise ValueError("Both username and password must be specified")
  else:
    username = args.username
    password = args.password

  icloud_photo_sync(username, password, args.download_dir, args.skip_exists, args.link_dir, args.remove_missing)

if __name__ == "__main__":
  main()
