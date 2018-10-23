from __future__ import division, print_function

import iotbx.pdb
from cctbx.array_family import flex
from libtbx import group_args
from libtbx.str_utils import make_sub_header

# =============================================================================
# Manager class for ALL ligands

class manager(dict):

  def __init__(self, model, log):
    self.model = model
    self.log   = log

  # ---------------------------------------------------------------------------

  def run(self):
    ph = self.model.get_hierarchy()
    ligand_isel_dict = self.get_ligands(ph = ph)
    for id_tuple, isel in ligand_isel_dict.items():
      for rg in ph.select(isel).residue_groups():
        ligand_dict = {}
        for conformer in rg.conformers():
          altloc = conformer.altloc
          conformer_isel = conformer.atoms().extract_i_seq()
          lr = ligand_result(
            model = self.model,
            isel = conformer_isel,
            id_str = rg.id_str())
          lr.get_occupancies()
          ligand_dict[altloc] = lr
      self[id_tuple] = ligand_dict

  # ---------------------------------------------------------------------------

  @staticmethod
  def get_ligands(ph):
    # Store ligands as list of iselections --> better way? Careful if H will be
    # added at some point!
    ligand_isel_dict = {}
    get_class = iotbx.pdb.common_residue_names_get_class
    exclude = ["common_amino_acid", "modified_amino_acid", "common_rna_dna",
               "modified_rna_dna", "ccp4_mon_lib_rna_dna", "common_water",
                "common_element"]
    for model in ph.models():
      for chain in model.chains():
        for rg in chain.residue_groups():
          for resname in rg.unique_resnames():
            if (not get_class(name=resname) in exclude):
              iselection = rg.atoms().extract_i_seq()
              id_tuple = (model.id, chain.id, rg.resseq)
              ligand_isel_dict[id_tuple] = iselection
    return ligand_isel_dict

  # ---------------------------------------------------------------------------

  def print_ligand_counts(self):
    make_sub_header("Ligands in input model", out=self.log)
    for id_tuple, ligand_dict in self.items():
      for altloc, lr in ligand_dict.items():
        print(lr.resname, lr.id_str, altloc)

  # ---------------------------------------------------------------------------

  def print_ligand_occupancies(self):
    make_sub_header("Occupancies", out=self.log)
    pad1 = ' '*20
    #print(pad1, "min    max    mean", file=self.log)
    print('If three values: min, max, mean, otherwise the same occupancy for entire ligand.', file=self.log)
    for id_tuple, ligand_dict in self.items():
      if len(ligand_dict) == 1:
        pad2 = ' '*8
        lr = ligand_dict.values()[0]
        occs = lr.get_occupancies()
        if (occs.occ_min == occs.occ_max):
          print(lr.resname, lr.id_str, pad2, occs.occ_min,
              file = self.log)
        else:
          print(lr.resname, lr.id_str, pad2, '%s   %s   %s' %
            (occs.occ_min, occs.occ_max, occs.occ_mean),
            file = self.log)
      else:
        pad2 = ' '*6
        for altloc, lr in ligand_dict.items():
          occs = lr.get_occupancies()
          if (occs.occ_min == occs.occ_max):
            print(lr.resname, lr.id_str, altloc, pad2, occs.occ_min,
              file = self.log)
          else:
            print(lr.resname, lr.id_str, altloc, pad2, '%s   %s   %s' %
              (occs.occ_min, occs.occ_max, occs.occ_mean),
              file = self.log)

# =============================================================================
# Class storing info per ligand

class ligand_result(object):

  def __init__(self, model, isel, id_str):
    self.model = model
    self.isel = isel
    self.id_str = id_str
    # results
    self._occupancies = None
    # to be used internally
    self.ph = self.model.get_hierarchy()
    self.atoms = self.ph.select(self.isel).atoms()

    #TODO: prob not necessary, let's see if we want to keep it
    rg_ligand = self.ph.select(self.isel).only_residue_group()
    self.resname = ",".join(rg_ligand.unique_resnames())

  # ---------------------------------------------------------------------------

  def get_occupancies(self):
    if self._occupancies is None:
      eps = 1.e-6
      occ = self.atoms.extract_occ()
      mmm = occ.min_max_mean()
      occ_min = mmm.min
      occ_max = mmm.max
      occ_mean = mmm.mean
      negative_count = (occ<0).count(True)
      negative_isel = (occ<0).iselection()
      zero_count = (flex.abs(occ)<eps).count(True)
      zero_isel = (flex.abs(occ)<eps).iselection()
      less_than_dot9_isel = (occ<0.9).iselection()

      return group_args(
      occ_min             = occ_min,
      occ_max             = occ_max,
      occ_mean            = occ_mean,
      negative_count      = negative_count,
      negative_isel       = negative_isel,
      zero_count          = zero_count,
      zero_isel           = zero_isel,
      less_than_dot9_isel = less_than_dot9_isel
      )

    return self._occupancies