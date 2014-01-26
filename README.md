Mopidy-Dictator
============

Rule mopidy with an iron fist.


<h3>Installation</h3>


Dictator replaces the standard MPD module, so you should disable it:

<pre>
[mpd]
enabled = false
</pre>

Dictator supports all the basic configurations used by standard MPD:

<pre>
[dictator]
enabled = false
password = 
hostname = 127.0.0.1
port = 6600
max_connections = 20
connection_timeout = 60
zeroconf = Mopidy MPD server on $hostname
</pre>

And some others.

<pre>
# a list of bad words. supports python's regex syntax.
bad_words = 
  fart(ing)?
  butt

# what to do when a bad word is encountered. [log, deny, both]
bad_word_action = deny

# matches bad words case insensitive
bad_word_case_insensitive = true

# a list of ip to user name mappings. should be formatted like '127.0.0.1:Me'
ip_list = 

# disables system mute command
disable_mute = true

# a log file for saving bad behavior
log_file = ~/.dictator_log

# when true, log_file is ignored and log is stored in memory
log_memory = false

# limits how many consecutive tracks a user can queue [0-20]. 0 means no limit
queue_limit = 0

# prevent songs from being played straight from search so they must be queued (COMING SOON)
disable_autoplay = false

# set to true if you're using the mopidy-spotify plugin
spotify_support = true
</pre>
