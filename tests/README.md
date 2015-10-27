There is a public Google Site which can be used to verify that the script works properly:
https://sites.google.com/site/backuptest102015

Make a local copy of this site on your computer, and then verify that the archive in GitHub and this local copy are the same.

# Example

```bash
# follow the installation instructions

git clone https://github.com/famzah/gdata-python-client.git
git clone https://github.com/famzah/google-sites-backup.git

# export the unit test Google Site

google-sites-backup/run.sh gdata-python-client/ google-sites-backup/ \
  --client_id='' \
  --client_secret='' \
  --domain='' \
  --site='backuptest102015' \
  --session_file=/var/tmp/gsites-token \
  --backup_dir=gdata-backup/

# verify that there are no differences

diff -r google-sites-backup/tests/site/backuptest102015 gdata-backup/site/backuptest102015
```
