from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import six

import numpy as np
from numpy import ma

from matplotlib.cbook import dedent
from matplotlib.ticker import (NullFormatter, ScalarFormatter,
                               LogFormatterSciNotation, LogitFormatter)
from matplotlib.ticker import (NullLocator, LogLocator, AutoLocator,
                               SymmetricalLogLocator, LogitLocator)
from matplotlib.transforms import Transform, IdentityTransform
from matplotlib import docstring


class ScaleBase(object):
    """
    The base class for all scales.

    Scales are separable transformations, working on a single dimension.

    Any subclasses will want to override:

      - :attr:`name`
      - :meth:`get_transform`
      - :meth:`set_default_locators_and_formatters`

    And optionally:
      - :meth:`limit_range_for_scale`
    """
    def get_transform(self):
        """
        Return the :class:`~matplotlib.transforms.Transform` object
        associated with this scale.
        """
        raise NotImplementedError()

    def set_default_locators_and_formatters(self, axis):
        """
        Set the :class:`~matplotlib.ticker.Locator` and
        :class:`~matplotlib.ticker.Formatter` objects on the given
        axis to match this scale.
        """
        raise NotImplementedError()

    def limit_range_for_scale(self, vmin, vmax, minpos):
        """
        Returns the range *vmin*, *vmax*, possibly limited to the
        domain supported by this scale.

        *minpos* should be the minimum positive value in the data.
         This is used by log scales to determine a minimum value.
        """
        return vmin, vmax


class LinearScale(ScaleBase):
    """
    The default linear scale.
    """

    name = 'linear'

    def __init__(self, axis, **kwargs):
        pass

    def set_default_locators_and_formatters(self, axis):
        """
        Set the locators and formatters to reasonable defaults for
        linear scaling.
        """
        axis.set_major_locator(AutoLocator())
        axis.set_major_formatter(ScalarFormatter())
        axis.set_minor_locator(NullLocator())
        axis.set_minor_formatter(NullFormatter())

    def get_transform(self):
        """
        The transform for linear scaling is just the
        :class:`~matplotlib.transforms.IdentityTransform`.
        """
        return IdentityTransform()


class LogTransformBase(Transform):
    input_dims = 1
    output_dims = 1
    is_separable = True
    has_inverse = True

    def __init__(self, nonpos):
        Transform.__init__(self)
        if nonpos == 'mask':
            self._fill_value = np.nan
        else:
            self._fill_value = 1e-300

    def transform_non_affine(self, a):
        with np.errstate(invalid="ignore"):
            a = np.where(a <= 0, self._fill_value, a)
        return np.divide(np.log(a, out=a), np.log(self.base), out=a)


class InvertedLogTransformBase(Transform):
    input_dims = 1
    output_dims = 1
    is_separable = True
    has_inverse = True

    def transform_non_affine(self, a):
        return ma.power(self.base, a)


class Log10Transform(LogTransformBase):
    base = 10.0

    def inverted(self):
        return InvertedLog10Transform()


class InvertedLog10Transform(InvertedLogTransformBase):
    base = 10.0

    def inverted(self):
        return Log10Transform()


class Log2Transform(LogTransformBase):
    base = 2.0

    def inverted(self):
        return InvertedLog2Transform()


class InvertedLog2Transform(InvertedLogTransformBase):
    base = 2.0

    def inverted(self):
        return Log2Transform()


class NaturalLogTransform(LogTransformBase):
    base = np.e

    def inverted(self):
        return InvertedNaturalLogTransform()


class InvertedNaturalLogTransform(InvertedLogTransformBase):
    base = np.e

    def inverted(self):
        return NaturalLogTransform()


class LogTransform(LogTransformBase):
    def __init__(self, base, nonpos):
        LogTransformBase.__init__(self, nonpos)
        self.base = base

    def inverted(self):
        return InvertedLogTransform(self.base)


class InvertedLogTransform(InvertedLogTransformBase):
    def __init__(self, base):
        InvertedLogTransformBase.__init__(self)
        self.base = base

    def inverted(self):
        return LogTransform(self.base)


class LogScale(ScaleBase):
    """
    A standard logarithmic scale.  Care is taken so non-positive
    values are not plotted.

    For computational efficiency (to push as much as possible to Numpy
    C code in the common cases), this scale provides different
    transforms depending on the base of the logarithm:

       - base 10 (:class:`Log10Transform`)
       - base 2 (:class:`Log2Transform`)
       - base e (:class:`NaturalLogTransform`)
       - arbitrary base (:class:`LogTransform`)
    """
    name = 'log'

    # compatibility shim
    LogTransformBase = LogTransformBase
    Log10Transform = Log10Transform
    InvertedLog10Transform = InvertedLog10Transform
    Log2Transform = Log2Transform
    InvertedLog2Transform = InvertedLog2Transform
    NaturalLogTransform = NaturalLogTransform
    InvertedNaturalLogTransform = InvertedNaturalLogTransform
    LogTransform = LogTransform
    InvertedLogTransform = InvertedLogTransform

    def __init__(self, axis, **kwargs):
        """
        *basex*/*basey*:
           The base of the logarithm

        *nonposx*/*nonposy*: ['mask' | 'clip' ]
          non-positive values in *x* or *y* can be masked as
          invalid, or clipped to a very small positive number

        *subsx*/*subsy*:
           Where to place the subticks between each major tick.
           Should be a sequence of integers.  For example, in a log10
           scale: ``[2, 3, 4, 5, 6, 7, 8, 9]``

           will place 8 logarithmically spaced minor ticks between
           each major tick.
        """
        if axis.axis_name == 'x':
            base = kwargs.pop('basex', 10.0)
            subs = kwargs.pop('subsx', None)
            nonpos = kwargs.pop('nonposx', 'mask')
        else:
            base = kwargs.pop('basey', 10.0)
            subs = kwargs.pop('subsy', None)
            nonpos = kwargs.pop('nonposy', 'mask')

        if nonpos not in ['mask', 'clip']:
            raise ValueError("nonposx, nonposy kwarg must be 'mask' or 'clip'")

        if base == 10.0:
            self._transform = self.Log10Transform(nonpos)
        elif base == 2.0:
            self._transform = self.Log2Transform(nonpos)
        elif base == np.e:
            self._transform = self.NaturalLogTransform(nonpos)
        else:
            self._transform = self.LogTransform(base, nonpos)

        self.base = base
        self.subs = subs

    def set_default_locators_and_formatters(self, axis):
        """
        Set the locators and formatters to specialized versions for
        log scaling.
        """
        axis.set_major_locator(LogLocator(self.base))
        axis.set_major_formatter(LogFormatterSciNotation(self.base))
        axis.set_minor_locator(LogLocator(self.base, self.subs))
        axis.set_minor_formatter(
            LogFormatterSciNotation(self.base,
                                    labelOnlyBase=self.subs))

    def get_transform(self):
        """
        Return a :class:`~matplotlib.transforms.Transform` instance
        appropriate for the given logarithm base.
        """
        return self._transform

    def limit_range_for_scale(self, vmin, vmax, minpos):
        """
        Limit the domain to positive values.
        """
        return (vmin <= 0.0 and minpos or vmin,
                vmax <= 0.0 and minpos or vmax)


class SymmetricalLogTransform(Transform):
    input_dims = 1
    output_dims = 1
    is_separable = True
    has_inverse = True

    def __init__(self, base, linthresh, linscale):
        Transform.__init__(self)
        self.base = base
        self.linthresh = linthresh
        self.linscale = linscale
        self._linscale_adj = (linscale / (1.0 - self.base ** -1))
        self._log_base = np.log(base)

    def transform_non_affine(self, a):
        sign = np.sign(a)
        masked = ma.masked_inside(a,
                                  -self.linthresh,
                                  self.linthresh,
                                  copy=False)
        log = sign * self.linthresh * (
            self._linscale_adj +
            ma.log(np.abs(masked) / self.linthresh) / self._log_base)
        if masked.mask.any():
            return ma.where(masked.mask, a * self._linscale_adj, log)
        else:
            return log

    def inverted(self):
        return InvertedSymmetricalLogTransform(self.base, self.linthresh,
                                               self.linscale)


class InvertedSymmetricalLogTransform(Transform):
    input_dims = 1
    output_dims = 1
    is_separable = True
    has_inverse = True

    def __init__(self, base, linthresh, linscale):
        Transform.__init__(self)
        symlog = SymmetricalLogTransform(base, linthresh, linscale)
        self.base = base
        self.linthresh = linthresh
        self.invlinthresh = symlog.transform(linthresh)
        self.linscale = linscale
        self._linscale_adj = (linscale / (1.0 - self.base ** -1))

    def transform_non_affine(self, a):
        sign = np.sign(a)
        masked = ma.masked_inside(a, -self.invlinthresh,
                                  self.invlinthresh, copy=False)
        exp = sign * self.linthresh * (
            ma.power(self.base, (sign * (masked / self.linthresh))
            - self._linscale_adj))
        if masked.mask.any():
            return ma.where(masked.mask, a / self._linscale_adj, exp)
        else:
            return exp

    def inverted(self):
        return SymmetricalLogTransform(self.base,
                                       self.linthresh, self.linscale)


class SymmetricalLogScale(ScaleBase):
    """
    The symmetrical logarithmic scale is logarithmic in both the
    positive and negative directions from the origin.

    Since the values close to zero tend toward infinity, there is a
    need to have a range around zero that is linear.  The parameter
    *linthresh* allows the user to specify the size of this range
    (-*linthresh*, *linthresh*).
    """
    name = 'symlog'
    # compatibility shim
    SymmetricalLogTransform = SymmetricalLogTransform
    InvertedSymmetricalLogTransform = InvertedSymmetricalLogTransform

    def __init__(self, axis, **kwargs):
        """
        *basex*/*basey*:
           The base of the logarithm

        *linthreshx*/*linthreshy*:
          The range (-*x*, *x*) within which the plot is linear (to
          avoid having the plot go to infinity around zero).

        *subsx*/*subsy*:
           Where to place the subticks between each major tick.
           Should be a sequence of integers.  For example, in a log10
           scale: ``[2, 3, 4, 5, 6, 7, 8, 9]``

           will place 8 logarithmically spaced minor ticks between
           each major tick.

        *linscalex*/*linscaley*:
           This allows the linear range (-*linthresh* to *linthresh*)
           to be stretched relative to the logarithmic range.  Its
           value is the number of decades to use for each half of the
           linear range.  For example, when *linscale* == 1.0 (the
           default), the space used for the positive and negative
           halves of the linear range will be equal to one decade in
           the logarithmic range.
        """
        if axis.axis_name == 'x':
            base = kwargs.pop('basex', 10.0)
            linthresh = kwargs.pop('linthreshx', 2.0)
            subs = kwargs.pop('subsx', None)
            linscale = kwargs.pop('linscalex', 1.0)
        else:
            base = kwargs.pop('basey', 10.0)
            linthresh = kwargs.pop('linthreshy', 2.0)
            subs = kwargs.pop('subsy', None)
            linscale = kwargs.pop('linscaley', 1.0)

        if base <= 1.0:
            raise ValueError("'basex/basey' must be larger than 1")
        if linthresh <= 0.0:
            raise ValueError("'linthreshx/linthreshy' must be positive")
        if linscale <= 0.0:
            raise ValueError("'linscalex/linthreshy' must be positive")

        self._transform = self.SymmetricalLogTransform(base,
                                                       linthresh,
                                                       linscale)

        self.base = base
        self.linthresh = linthresh
        self.linscale = linscale
        self.subs = subs

    def set_default_locators_and_formatters(self, axis):
        """
        Set the locators and formatters to specialized versions for
        symmetrical log scaling.
        """
        axis.set_major_locator(SymmetricalLogLocator(self.get_transform()))
        axis.set_major_formatter(LogFormatterSciNotation(self.base))
        axis.set_minor_locator(SymmetricalLogLocator(self.get_transform(),
                                                     self.subs))
        axis.set_minor_formatter(NullFormatter())

    def get_transform(self):
        """
        Return a :class:`SymmetricalLogTransform` instance.
        """
        return self._transform


class LogitTransform(Transform):
    input_dims = 1
    output_dims = 1
    is_separable = True
    has_inverse = True

    def __init__(self, nonpos):
        Transform.__init__(self)
        if nonpos == 'mask':
            self._fill_value = np.nan
        else:
            self._fill_value = 1e-300
        self._nonpos = nonpos

    def transform_non_affine(self, a):
        """logit transform (base 10), masked or clipped"""
        with np.errstate(invalid="ignore"):
            a = np.select(
                [a <= 0, a >= 1], [self._fill_value, 1 - self._fill_value], a)
        return np.log10(a / (1 - a))

    def inverted(self):
        return LogisticTransform(self._nonpos)


class LogisticTransform(Transform):
    input_dims = 1
    output_dims = 1
    is_separable = True
    has_inverse = True

    def __init__(self, nonpos='mask'):
        Transform.__init__(self)
        self._nonpos = nonpos

    def transform_non_affine(self, a):
        """logistic transform (base 10)"""
        return 1.0 / (1 + 10**(-a))

    def inverted(self):
        return LogitTransform(self._nonpos)


class LogitScale(ScaleBase):
    """
    Logit scale for data between zero and one, both excluded.

    This scale is similar to a log scale close to zero and to one, and almost
    linear around 0.5. It maps the interval ]0, 1[ onto ]-infty, +infty[.
    """
    name = 'logit'

    def __init__(self, axis, nonpos='mask'):
        """
        *nonpos*: ['mask' | 'clip' ]
          values beyond ]0, 1[ can be masked as invalid, or clipped to a number
          very close to 0 or 1
        """
        if nonpos not in ['mask', 'clip']:
            raise ValueError("nonposx, nonposy kwarg must be 'mask' or 'clip'")

        self._transform = LogitTransform(nonpos)

    def get_transform(self):
        """
        Return a :class:`LogitTransform` instance.
        """
        return self._transform

    def set_default_locators_and_formatters(self, axis):
        # ..., 0.01, 0.1, 0.5, 0.9, 0.99, ...
        axis.set_major_locator(LogitLocator())
        axis.set_major_formatter(LogitFormatter())
        axis.set_minor_locator(LogitLocator(minor=True))
        axis.set_minor_formatter(LogitFormatter())

    def limit_range_for_scale(self, vmin, vmax, minpos):
        """
        Limit the domain to values between 0 and 1 (excluded).
        """
        return (vmin <= 0 and minpos or vmin,
                vmax >= 1 and (1 - minpos) or vmax)


_scale_mapping = {
    'linear': LinearScale,
    'log':    LogScale,
    'symlog': SymmetricalLogScale,
    'logit':  LogitScale,
    }


def get_scale_names():
    names = list(six.iterkeys(_scale_mapping))
    names.sort()
    return names


def scale_factory(scale, axis, **kwargs):
    """
    Return a scale class by name.

    ACCEPTS: [ %(names)s ]
    """
    scale = scale.lower()
    if scale is None:
        scale = 'linear'

    if scale not in _scale_mapping:
        raise ValueError("Unknown scale type '%s'" % scale)

    return _scale_mapping[scale](axis, **kwargs)
scale_factory.__doc__ = dedent(scale_factory.__doc__) % \
    {'names': " | ".join(get_scale_names())}


def register_scale(scale_class):
    """
    Register a new kind of scale.

    *scale_class* must be a subclass of :class:`ScaleBase`.
    """
    _scale_mapping[scale_class.name] = scale_class


def get_scale_docs():
    """
    Helper function for generating docstrings related to scales.
    """
    docs = []
    for name in get_scale_names():
        scale_class = _scale_mapping[name]
        docs.append("    '%s'" % name)
        docs.append("")
        class_docs = dedent(scale_class.__init__.__doc__)
        class_docs = "".join(["        %s\n" %
                              x for x in class_docs.split("\n")])
        docs.append(class_docs)
        docs.append("")
    return "\n".join(docs)


docstring.interpd.update(
    scale=' | '.join([repr(x) for x in get_scale_names()]),
    scale_docs=get_scale_docs().rstrip(),
    )
