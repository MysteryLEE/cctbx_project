from __future__ import absolute_import, division, print_function
from libtbx.utils import null_out
from scitbx.array_family import flex
'''
Mask utilities
'''

class create_mask_around_atoms(object):

  '''
    Class to create a map_manager object containing a mask around atoms,
    smooth or adjust density outside, and apply to a supplied map_manager

  '''

  def __init__(self,
      model = None,
      xray_structure = None,
      mask_atoms_atom_radius = None,
      n_real = None,
      map_manager = None):

    '''
     Create a mask (map object) with values of 1 near atoms in xray_structure

     Parameters are:
       model:   required source of information about where atoms are
       xray_structure:   alternate source of information about where atoms are
       mask_atoms_atom_radius:  radius around atoms to mask
       n_real:  dimensions of map to create, e.g., existing map_data.all()
       map_manager: alternate source of information for n_real. origin (0, 0, 0)
    '''

    assert (model is not None) or (xray_structure is not None)
    assert mask_atoms_atom_radius is not None
    assert (n_real is not None) or (map_manager is not None)

    if not n_real:
      assert map_manager.map_data().origin() == (0, 0, 0)
      n_real = map_manager.map_data().all()


    if model:
      xray_structure = model.get_xray_structure()
      self._crystal_symmetry = model.crystal_symmetry()
    else:
      self._crystal_symmetry = xray_structure.crystal_symmetry()

    import boost.python
    cctbx_maptbx_ext = boost.python.import_ext("cctbx_maptbx_ext")
    radii = flex.double(
      xray_structure.sites_frac().size(), mask_atoms_atom_radius)
    self._mask = cctbx_maptbx_ext.mask(
      sites_frac                  = xray_structure.sites_frac(),
      unit_cell                   = xray_structure.unit_cell(),
      n_real                      = n_real,
      mask_value_inside_molecule  = 1,
      mask_value_outside_molecule = 0,
      radii                       = radii)
    # Set up map_manager with this mask
    if map_manager:
      self._map_manager = map_manager.customized_copy(map_data = self._mask)
    else:
      from iotbx.map_manager import map_manager as map_man
      self._map_manager = map_man(map_data = self._mask,
        unit_cell_crystal_symmetry = self.crystal_symmetry(),
        unit_cell_grid = self._mask.all())

    self._map_manager.set_is_mask(True)

    # Initialize soft mask
    self._is_soft_mask = False
    self._is_soft_mask_around_edges = False

  def mask(self):
    return self._mask

  def map_manager(self):
    return self._map_manager

  def is_soft_mask_around_edges(self):
    return self._is_soft_mask_around_edges

  def is_soft_mask(self):
    return self._is_soft_mask

  def solvent_content(self):
    if hasattr(self, '_solvent_content'):
      return self._solvent_content

  def crystal_symmetry(self):
    return self._crystal_symmetry

  def soft_mask(self, soft_mask_radius = None):
    '''
    Make the mask a soft mask
    Parameter:
      soft_mask_radius:   defines distance over which mask is smoothed
    '''
    assert soft_mask_radius is not None
    assert not self.is_soft_mask()  # do not do it twice

    from cctbx.maptbx.segment_and_split_map import smooth_mask_data

    self._mask = smooth_mask_data(mask_data = self._mask,
      crystal_symmetry = self._crystal_symmetry,
       rad_smooth = soft_mask_radius)

  def soft_mask_around_edges(self,
      resolution = None,
      soft_mask_radius = None, ):
    '''
    Create a new soft mask around the edges of box

    Parameters:
      resolution:    Resolution to be used in smoothing
      soft_mask_radius:   Distance over which the edge mask affects the map

    '''
    # Checks:
    assert resolution is not None

    if soft_mask_radius is None:
      soft_mask_radius = resolution
    assert not self.is_soft_mask_around_edges()  # do not do it twice

    from cctbx.maptbx.segment_and_split_map import get_zero_boundary_map, \
        smooth_mask_data

    zero_boundary_map = get_zero_boundary_map(
      map_data = self._map_manager.map_data(),
      crystal_symmetry = self.box_crystal_symmetry,
      radius = soft_mask_radius)

    original_mask_data = zero_boundary_map.deep_copy()

    self._mask= smooth_mask_data(mask_data = zero_boundary_map,
      crystal_symmetry = self.box_crystal_symmetry,
      rad_smooth = soft_mask_radius)
    self._is_soft_mask_around_edges = True

  def apply_mask_to_other_map_manager(self, other_map_manager = None,
     set_outside_to_mean_inside = False,
     set_mean_to_zero = False):

    '''
    Apply this mask to a map_manager object containing map_data.
    Creates new map_manager

    Parameters:
       other_map_manager: map_manager to be masked in place
       set_outside_to_mean_inside:  if True,
          set the value outside mask to the mean inside the mask
       set_mean_to_zero:  Adjust overall mean of map to zero after masking
    '''

    assert other_map_manager.is_similar(self.map_manager())
    assert other_map_manager.map_data().origin() == (0, 0, 0)

    from cctbx.maptbx.segment_and_split_map import apply_mask_to_map
    new_map_data = apply_mask_to_map(mask_data = self._mask,
      smoothed_mask_data = self._mask,
      set_outside_to_mean_inside = set_outside_to_mean_inside,
      set_mean_to_zero = set_mean_to_zero,
      map_data = other_map_manager.map_data(),
      out = null_out())

    return self.map_manager().customized_copy(map_data = new_map_data)

class create_mask_around_edges(create_mask_around_atoms):

  '''
    Class to create a map_manager object containing a mask a few pixels in
    around the boundaries of the map

  '''

  def __init__(self,
      soft_mask_radius = None,
      map_manager = None):

    '''
     Create a mask (map object) with values of 1 except at the map boundaries

     Parameters are:
       soft_mask_radius:  radius for masking
       map_manager: source of information for n_real and crystal_symmetryi
          . origin (0, 0, 0)
    '''

    assert soft_mask_radius is not None
    assert (map_manager is not None)

    n_real = map_manager.map_data().all()

    self._crystal_symmetry = map_manager.crystal_symmetry()

    from cctbx.maptbx.segment_and_split_map import get_zero_boundary_map

    self._mask = get_zero_boundary_map(
      map_data = map_manager.map_data(),
      crystal_symmetry = self._crystal_symmetry,
      radius = soft_mask_radius)
    # Set up map_manager with this mask
    self._map_manager = map_manager.customized_copy(map_data = self._mask)
    self._map_manager.set_is_mask(True)

    # Initialize soft mask
    self._is_soft_mask = False
    self._is_soft_mask_around_edges = False

class create_mask_around_density(create_mask_around_atoms):

  '''
    Class to create a map_manager object containing a mask around density

  '''

  def __init__(self,
      map_manager = None,
      resolution = None,
      molecular_mass = None,
      sequence = None,
      solvent_content = None):

    '''
     Create a mask (map object) with values of 1 near molecule

     Parameters are:
       map_manager: source of information about density
       resolution : optional resolution of map
       molecular_mass: optional mass (Da) of object in density
       sequence: optional sequence of object in density
       solvent_content : optional solvent_content of map
    '''

    assert (map_manager is not None)

    if not resolution:
      from cctbx.maptbx import d_min_from_map
      resolution = d_min_from_map(
           map_data=map_manager.map_data(),
           unit_cell=map_manager.crystal_symmetry().unit_cell())

    self._crystal_symmetry = map_manager.crystal_symmetry()

    if (molecular_mass or sequence ) and (
          not solvent_content):
      # Try to get a good starting value of solvent_content

      from cctbx.maptbx.segment_and_split_map import get_solvent_fraction
      solvent_content = get_solvent_fraction(
           params = None,
           molecular_mass = molecular_mass,
           sequence = sequence,
           do_not_adjust_dalton_scale = True,
           crystal_symmetry = self._crystal_symmetry,
           out = null_out())

    # Now use automatic procedure to get a mask
    from cctbx.maptbx.segment_and_split_map import \
          get_iterated_solvent_fraction

    self._mask, self._solvent_content = get_iterated_solvent_fraction(
          crystal_symmetry = self._crystal_symmetry,
          fraction_of_max_mask_threshold = 0.05, #
          solvent_content = solvent_content,
          cell_cutoff_for_solvent_from_mask = 1, # Use low-res method always
          use_solvent_content_for_threshold = True,
          mask_resolution = resolution,
          return_mask_and_solvent_fraction = True,
          map = map_manager.map_data(),
          verbose = False,
          out = null_out())

    if self._solvent_content is None:
      raise Sorry("Unable to get solvent content in auto-masking")


    # Set up map_manager with this mask
    self._map_manager = map_manager.customized_copy(map_data = self._mask)
    self._map_manager.set_is_mask(True)

    # Initialize soft mask
    self._is_soft_mask = False
    self._is_soft_mask_around_edges = False