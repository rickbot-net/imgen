# Starting meme-server
install rethinkdb [here](https://github.com/rethinkdb/rethinkdb) and get that running

```bash
git clone
cd imgen
./start.sh
```

The core will stay the same, I'm only updating old stuff here (:


# RethinkDB settings
- Create DB called "meme"
    - Tables
      - applications
      - keys


# Redis

- Run redis server
  - Redis port: 6379

# Bot configuration

> create "config.json" file with the following contents

```json
{
  "client_id": "699724677341380720",
  "client_secret": "SeXP_DdSlAvavaILEAa-Q2yQwKC4zP9H9A",
  "admins": ["186571646453284864", "188418994527535104"],
  "rdb_address": "localhost",
  "rdb_port": 28015,
  "rdb_db": "meme"
}
```


