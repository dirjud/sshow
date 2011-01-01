# Note: plugindir is set in configure

plugin_LTLIBRARIES = libgstkenburns.la

##############################################################################
# TODO: for the next set of variables, name the prefix if you named the .la, #
#  e.g. libmysomething.la => libmysomething_la_SOURCES                       #
#                            libmysomething_la_CFLAGS                        #
#                            libmysomething_la_LIBADD                        #
#                            libmysomething_la_LDFLAGS                       #
##############################################################################

# sources used to compile this plug-in
libgstkenburns_la_SOURCES = gstkenburns.c gstkenburns.h

# compiler and linker flags used to compile this plugin, set in configure.ac
libgstkenburns_la_CFLAGS = $(GST_CFLAGS) 
libgstkenburns_la_LIBADD = $(GST_LIBS) -lgstvideo-0.10
libgstkenburns_la_LDFLAGS = $(GST_PLUGIN_LDFLAGS)
libgstkenburns_la_LIBTOOLFLAGS = --tag=disable-static

# headers we need but don't want installed
noinst_HEADERS = gstkenburns.h
