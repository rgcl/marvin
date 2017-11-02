#!/usr/bin/env python
# encoding: utf-8
#
# @Author: José Sánchez-Gallego
# @Date: Oct 30, 2017
# @Filename: datacube.py
# @License: BSD 3-Clause
# @Copyright: José Sánchez-Gallego


from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import numpy as np

from astropy import units

from .base_quantity import QuantityMixIn
from .spectrum import Spectrum


class DataCube(units.Quantity, QuantityMixIn):
    """A `~astropy.units.Quantity`-powered representation of a 3D data cube.

    A `DataCube` represents a 3D array in which two of the dimensions
    correspond to the spatial direction, with the third one being the
    spectral direction.

    Parameters:
        value (`~numpy.ndarray`):
            A 3-D array with the value of the quantity measured. The first
            axis of the array must be the wavelength dimension.
        wavelength (`~numpy.ndarray`):
            A 1-D array with the wavelength of each spectral measurement. It
            must have the same length as the spectral dimesion of ``value``.
        unit (`~astropy.units.Unit`):
            An `astropy unit <astropy.units.Unit>` with the units for
            ``value``.
        scale (float):
            The scale factor of the spectrum value.
        wavelength_unit (astropy.unit.Unit):
            The units of the wavelength solution. Defaults to Angstrom.
        redcorr (`~numpy.ndarray`):
            The reddenning correction, used by `.ModelCube.deredden`.
        ivar (`~numpy.ndarray`):
            An array with the same shape as ``value`` contianing the associated
            inverse variance.
        mask (`~numpy.ndarray`):
            Same as ``ivar`` but for the associated
            :ref:`bitmask <marvin-bitmasks>`.
        kwargs (dict):
            Keyword arguments to be passed to `~astropy.units.Quantity` when
            it is initialised.

    """

    def __new__(cls, value, wavelength, scale=None, unit=units.dimensionless_unscaled,
                wavelength_unit=units.Angstrom, redcorr=None, ivar=None, mask=None, dtype=None,
                copy=True, **kwargs):

        # If the scale is defined, creates a new composite unit with the input scale.
        if scale is not None:
            unit = units.CompositeUnit(unit.scale * scale, unit.bases, unit.powers)

        assert wavelength is not None, 'a valid wavelength array is required'

        assert isinstance(value, np.ndarray) and value.ndim == 3, 'value must be a 3D array.'
        assert isinstance(wavelength, np.ndarray) and wavelength.ndim == 1, \
            'wavelength must be a 1D array.'
        assert len(wavelength) == value.shape[0], \
            'wavelength and value spectral dimensions do not match'

        if ivar is not None:
            assert isinstance(ivar, np.ndarray) and ivar.shape == value.shape, 'invalid ivar shape'
            assert isinstance(mask, np.ndarray) and mask.shape == value.shape, 'invalid mask shape'

        obj = units.Quantity(value, unit=unit, **kwargs)
        obj = obj.view(cls)
        obj._set_unit(unit)

        assert wavelength is not None, 'invalid wavelength'

        if isinstance(wavelength, units.Quantity):
            obj.wavelength = wavelength
        else:
            obj.wavelength = np.array(wavelength) * wavelength_unit

        obj.ivar = np.array(ivar) if ivar is not None else None
        obj.mask = np.array(mask) if mask is not None else None

        if redcorr is not None:
            assert len(redcorr) == len(obj.wavelength), 'invalid length for redcorr.'
            obj.redcorr = np.array(redcorr)

        return obj

    def __getitem__(self, sl):

        if isinstance(sl, tuple):
            sl_wave = sl[0]
        else:
            sl_wave = sl

        new_obj = super(DataCube, self).__getitem__(sl)

        if type(new_obj) is not type(self):
            new_obj = self._new_view(new_obj)

        new_obj._set_unit(self.unit)

        new_obj.ivar = self.ivar.__getitem__(sl) if self.ivar is not None else self.ivar
        new_obj.mask = self.mask.__getitem__(sl) if self.mask is not None else self.mask
        new_obj.wavelength = self.wavelength.__getitem__(sl_wave) \
            if self.wavelength is not None else self.wavelength
        new_obj.redcorr = self.redcorr.__getitem__(sl_wave) \
            if self.redcorr is not None else self.redcorr

        if new_obj.ndim == 1 and not np.isscalar(new_obj.wavelength):
            return Spectrum(new_obj.value, unit=new_obj.unit, wavelength=new_obj.wavelength,
                            ivar=new_obj.ivar, mask=new_obj.mask)

        return new_obj

    def __array_finalize__(self, obj):

        if obj is None:
            return

        self.wavelength = getattr(obj, 'wavelength', None)
        self.ivar = getattr(obj, 'ivar', None)
        self.mask = getattr(obj, 'mask', None)
        self.redcorr = getattr(obj, 'redcorr', None)

    def derredden(self):
        """Returns the derreddened datacube."""

        new_value = (self.value.T * self.redcorr).T

        new_obj = DataCube(new_value, self.wavelength, unit=self.unit,
                           redcorr=None, ivar=self, mask=self)

        return new_obj