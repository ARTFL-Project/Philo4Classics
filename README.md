# Philo4Classics

This package contains extensive customizations for PhiloLogic 4.6, allowing for sensible parsing and display of Perseus-like Greek and Latin texts.
You can download PhiloLogic 4.6 from github [here](https://github.com/ARTFL-Project/PhiloLogic4/tree/PhiloLogic-4.6). Philo4Classics will not currently work with version 4.7, but we hope to extend support to it in future development.

If you are having trouble installing PhiloLogic 4.6, you can check our installation tips [here](P46INSTALL.md).

Included:

- custom runtime and loadtime functions
- a `classicize.py` script which makes common adjustments to the PhiloLogic 4.6 app

## Usage

Make sure you set the correct paths for `philo4classics` and `lexicon_db` in `Classics_load_config.py`.

```python
# Define location of local Philo4Classics load directory
philo4classics = "/my/path/to/Philo4Classics/load"

# Default path to Greek Lexicon if different from philo4classics
lexicon_db = "/var/www/cgi-bin/perseus/GreekLexicon16.db"
```

The load should be done from the `load/` directory:

```bash
cd /path/to/Philo4Classics/load
philoload4 -l Classics_load_config.py MyNewLoad /path/to/my/file*.xml
```

Make sure that you set the correct path for `philologic_path` in `classicize.py`.

```python
philologic_path="/var/www/html/philologic4/"
```

Unless there are good reasons, the `classicize.py` script should be run after all Philo4Classics custom loads, *but before you do so, make sure to try to load the database in a browser first so that the PhiloLogic4 app initializes certain files:*

```bash
./classicize.py MyLoad # parameters are optional
```

- the optional parameters are "dictionary" and "text" to be used with dictionary loads and text loads, respectively (if not sure, use the "text" parameter)
- if the "no" parameter is used, then only those adjustments which are common to all Philo4Classics loads will be applied (this is usually the wrong choice).
