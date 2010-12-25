#include <Python.h>
#include <structmember.h>
#include <gdk-pixbuf/gdk-pixbuf.h>

enum {
  RGB = 1,
  YUV = 2,
};


static void __rgb2yCrCb(int r, int g, int b, int *y, int *Cr, int *Cb) {
  *y  =       (19595*r + 38470*g +  7471*b) / 65536;
  *Cb = 128 - (11010*r - 21710*g + 32768*b) / 65536;
  *Cr = 128 + (36372*r - 27439*g -  5329*b) / 65536;
}

static void __yCrCb2rgb(int y, int Cr, int Cb, int *r, int *g, int *b) {
  int A  = y;
  int B  = -(Cb-128);
  int R  = (Cr-128);
  *r = -136784 * A +             +  191776 * R;
  *g =  197847 * A +  -29212 * B +  -97745 * R;
  *b =  -85122 * A +  150426 * B +     323 * R;
}


typedef struct {
  PyObject_HEAD
  int width;
  int height;
  int format;
  union {
    int *y;
    int *r;
  };
  union {
    int *Cr;
    int *g;
  };
  union {
    int *Cb;
    int *b;
  };
} imgObject;

static void img_dealloc(imgObject* self) {
  if(self->r) { free(self->r); }
  if(self->g) { free(self->g); }
  if(self->b) { free(self->b); }
  self->r = self->g = self->b = NULL;
  self->ob_type->tp_free((PyObject*)self);
}

static PyObject *img_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
    imgObject *self;
    self = (imgObject *)type->tp_alloc(type, 0);
    if (self != NULL) {
      self->width = self->height = self->format = -1;
      self->y = self->Cr = self->Cb = NULL;
    }
    return (PyObject *)self;
}

static int __img_init(imgObject *self, int width, int height, int format) {
  if( width <= 0 || height <= 0 ) {
    return -1;
  }
  self->width = width;
  self->height = height;
  self->format = format;
  if(format == RGB) {
    self->r = (int *) calloc(width*height, sizeof(self->r));
    self->g = (int *) calloc(width*height, sizeof(self->g));
    self->b = (int *) calloc(width*height, sizeof(self->b));
  } else if(format == YUV) {
    self->y  = (int *) calloc(width*height, sizeof(self->r));
    self->Cr = (int *) calloc(width*height, sizeof(self->g));
    self->Cb = (int *) calloc(width*height, sizeof(self->b));
  } else {
    return -1;
  }
  if(!self->y || !self->Cr || !self->Cb) {
    return -1;
  }
  return 0;
}

static int img_init(imgObject *self, PyObject *args, PyObject *kwds) {
  int width=0, height=0, format=1;
  static char *kwlist[] = {"width", "height", "format", NULL};
  if (! PyArg_ParseTupleAndKeywords(args, kwds, "iii", kwlist, 
				    &width, &height, &format))
    return -1; 

  return __img_init(self, width, height, format);
}

static PyObject *scale_and_crop(imgObject *self, PyObject *args, PyObject *kw) {
  int up, down, row, col, xs, ys, poss, posd, y, Cr, Cb;
  double x0, y0;
  imgObject *dest = NULL;
  static char *kwlist[] = {"down", "up", "x0", "y0", "dest", NULL};

  if (!PyArg_ParseTupleAndKeywords(args, kw, "iiddO", kwlist, &down, &up, &x0, &y0, &dest))
    return NULL;
 
  if(self->format != YUV) {
    PyErr_SetString(PyExc_Exception, "source image must be in YUV format.");
    return NULL;
  }

  if(dest->format == RGB) {
    for(row=0; row < dest->height; row++) {
      for(col=0; col < dest->width; col++) {
	xs = x0 + (col + 0.5) * down / up;
	ys = y0 + (row + 0.5) * down / up;
	poss = xs + ys*self->width;
	y  = self->y[poss];
	Cr = self->Cr[poss];
	Cb = self->Cb[poss];
	posd = row*dest->width + col;
	__yCrCb2rgb(y,Cr,Cb, dest->r+posd, dest->g+posd, dest->b+posd);
      }
    }
  }
  Py_RETURN_NONE;
}

static PyObject *write_img(imgObject *self, PyObject *args, PyObject *kw) {
  int i;
  char *filename = NULL;
  static char *kwlist[] = {"filename", NULL};

  if (!PyArg_ParseTupleAndKeywords(args, kw, "s", kwlist, &filename))
    return NULL;

  if(self->format != RGB) {
    PyErr_SetString(PyExc_Exception, "source image must be in RGB format.");
    return NULL;
  }
  FILE *f = fopen(filename, "w");
  if(!f) {
    PyErr_SetString(PyExc_Exception, "Cannot open file for writing");
    return NULL;
  }
  fprintf(f, "P6\n%d %d\n255\n", self->width, self->height);
  for(i=0;i<self->width*self->height;i++) {
    fputc(self->r[i], f);
    fputc(self->g[i], f);
    fputc(self->b[i], f);
  }
  fclose(f);
  Py_RETURN_NONE;
}

static PyMethodDef imgo_methods[] = {
    {"scale_and_crop", (PyCFunction) scale_and_crop, METH_VARARGS | METH_KEYWORDS,
     "Pass in a tuple of upper left crop position, a downsample factor, an up sample factor, and an image into which the new result will be placed." },
    {"write", (PyCFunction) write_img, METH_VARARGS | METH_KEYWORDS, ""},
    {NULL}  /* Sentinel */
};

static PyMemberDef img_members[] = {
  {"width",  T_INT, offsetof(imgObject, width),  0, "image width"},
  {"height", T_INT, offsetof(imgObject, height), 0, "image height"},
  {"format", T_INT, offsetof(imgObject, format), 0, "image format"},
  {NULL}  /* Sentinel */
};

static PyTypeObject imgType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "SlideShow.Image",         /*tp_name*/
    sizeof(imgObject),         /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor) img_dealloc, /*tp_dealloc*/
    0,                         /*tp_print*/
    0,                         /*tp_getattr*/
    0,                         /*tp_setattr*/
    0,                         /*tp_compare*/
    0,                         /*tp_repr*/
    0,                         /*tp_as_number*/
    0,                         /*tp_as_sequence*/
    0,                         /*tp_as_mapping*/
    0,                         /*tp_hash */
    0,                         /*tp_call*/
    0,                         /*tp_str*/
    0,                         /*tp_getattro*/
    0,                         /*tp_setattro*/
    0,                         /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT,        /*tp_flags*/
    "Image",                   /* tp_doc */
    0,		               /* tp_traverse */
    0,		               /* tp_clear */
    0,		               /* tp_richcompare */
    0,		               /* tp_weaklistoffset */
    0,		               /* tp_iter */
    0,		               /* tp_iternext */
    imgo_methods,             /* tp_methods */
    img_members,             /* tp_members */
    0,                         /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)img_init,      /* tp_init */
    0,                         /* tp_alloc */
    img_new,                 /* tp_new */
};

static imgObject* read_file(char *filename, int format) {
  imgObject *img, *ret = NULL;
  GError *gerror = NULL;
  GdkPixbuf *pixbuf = gdk_pixbuf_new_from_file(filename, &gerror);
  if(!pixbuf) {
    PyErr_SetString(PyExc_Exception, "Cannot read in file");
    goto cleanup0;
  }
  int channels  = gdk_pixbuf_get_n_channels(pixbuf);
  if(channels!=3) {
    PyErr_SetString(PyExc_Exception, "Unsupported image.");
    goto cleanup1;
  }

  img = (imgObject *) img_new(&imgType, NULL, NULL);
  if(__img_init(img, 
		gdk_pixbuf_get_width(pixbuf),
		gdk_pixbuf_get_height(pixbuf),
		format) == -1) {
    PyErr_SetString(PyExc_Exception, "Error creating image");
    goto cleanup1;
  }
     

  guint8 *ibuf = gdk_pixbuf_get_pixels(pixbuf);
  int size     = img->width*img->height;
  int ipos=0, opos=0;
  if(format == RGB) {
    for(opos=0,ipos=0; opos<size; ++opos) {
      img->r[opos] = ibuf[ipos++]; 
      img->g[opos] = ibuf[ipos++]; 
      img->b[opos] = ibuf[ipos++]; 
    }
  } else if(format == YUV) {
    int r,g,b;
    for(opos=0,ipos=0; opos<size; ++opos) {
      r = ibuf[ipos++]; 
      g = ibuf[ipos++]; 
      b = ibuf[ipos++]; 
      __rgb2yCrCb(r, g, b, img->y+opos, img->Cr+opos, img->Cb+opos);
    }
  }
  ret = img;
 cleanup1:  
  g_object_unref(pixbuf);
 cleanup0:
  if(!ret)
    img_dealloc(img);
  return ret;
}
static PyObject *py_read_file(PyObject *self, PyObject *args, PyObject *kw) {
    int format = RGB;
    char *filename = NULL;

    static char *kwlist[] = {"filename", "format", NULL};

    if (!PyArg_ParseTupleAndKeywords(args, kw, "s|i", kwlist, &filename, &format))
        return NULL;

    return (PyObject *) read_file(filename, format);
}


static PyMethodDef img_methods[] = {
  {"read", (PyCFunction) py_read_file, METH_VARARGS | METH_KEYWORDS, "Read image file" },
  {NULL}  /* Sentinel */
};

#ifndef PyMODINIT_FUNC	/* declarations for DLL import/export */
#define PyMODINIT_FUNC void
#endif
PyMODINIT_FUNC
initImage(void) 
{
  PyObject* m;
  g_type_init();
  
  imgType.tp_new = PyType_GenericNew;
  if (PyType_Ready(&imgType) < 0)
    return;
  
  m = Py_InitModule3("Image", img_methods,
		     "Image module");
  
  Py_INCREF(&imgType);
  PyModule_AddObject(m, "Image", (PyObject *)&imgType);
  PyModule_AddObject(m, "RGB", PyInt_FromLong(RGB));
  PyModule_AddObject(m, "YUV", PyInt_FromLong(YUV));
}
