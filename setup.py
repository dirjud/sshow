from distutils.core import setup, Extension
import commands

def pkgconfig(*packages, **kw):
    flag_map = {'-I': 'include_dirs', '-L': 'library_dirs', '-l': 'libraries'}
    cmd = "pkg-config --libs --cflags %s" % ' '.join(packages)
    for token in commands.getoutput(cmd).split():
        if flag_map.has_key(token[:2]):
            kw.setdefault(flag_map.get(token[:2]), []).append(token[2:])
        else: # throw others to extra_link_args
            kw.setdefault('extra_link_args', []).append(token)

        for k, v in kw.iteritems(): # remove duplicated
            kw[k] = list(set(v))
    return kw


setup (name = 'SlideShow',
       version = '1.0',
       description = 'SlideShow package',
       author = 'Lane Brooks',
       author_email = 'dirjud@gmail.com',
       url = '',
       packages = ['SlideShow', 'SlideShow.pygtk' ],
       package_dir = { 'SlideShow'      : "src/SlideShow",
                       'SlideShow.pygtk': "src/SlideShow/pygtk",
                       },
       package_data = { 'SlideShow.pygtk' : [ '*.glade', '*.png'],
                        },
       scripts = [ 'src/sscompile','src/ssdesign', 'src/sspreview' ],
       )
