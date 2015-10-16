# google-sites-backup
Export a Google Site and save it locally on your computer.

## Installation

```bash
mkdir ~/backup
cd ~/backup
git clone https://github.com/google/gdata-python-client.git
git clone https://github.com/famzah/google-sites-backup.git
```

## Interactive execution

The default behavior is to ask for every configuration setting on the console:
```bash
google-sites-backup/run.sh gdata-python-client/ google-sites-backup/
```

## Non-interactive execution

If you intent to run the backup script multiple times, you should consider the following approach:
```bash
google-sites-backup/run.sh gdata-python-client/ google-sites-backup/ \
  --client_id='%YOUR-OAUTH2-ID%' \
  --client_secret='%YOUR-OAUTH2-SECRET%' \
  --domain='%EMPTY_OR_ENTER_GOOGLE_APPS_DOMAIN%' \
  --site='mywikiexample' \
  --session_file=/var/tmp/gsites-token \
  --backup_dir=gdata-backup/
```

Notes:
* The "gdata-backup/" target directory must not exist.
* The "session_file" caches the authentication token, so that you don't have to switch to a browser and authorize the client for every site you want to backup.
* For most users, the "domain" option should be an empty string ''.
* You need your own OAuth 2.0 credentials:
  * Create a new project in the [Google Developers Console](https://console.developers.google.com/) on your account.
  * Activate the "Google Sites Data" API in the Google Developers Console. Navigate to "APIs & auth", then "APIs". If the API isn't listed in the Developers Console, then skip this step.
  * In the Google Developers Console, navigate to "APIs & auth", then "Credentials". Click the button "Add credentials" and choose "OAuth 2.0 client ID". Choose "other" for "Application type".
  * You can now see and use your client ID and client secret.

## Alternative implementations

The [Google Sites Liberation](https://github.com/sih4sing5hong5/google-sites-liberation) project is written in Java. As of its latest release, it works only in GUI mode since OAuth2 is not supported in the non-interactive console mode. Future versions may fix this, so check regularly if this solution suits you better.
