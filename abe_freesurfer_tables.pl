#!/usr/bin/env perl
#
# freesurfer_tables.pl
#
# Description
#   Collect all longitudinal FreeSurfer results into summary tables
#
# Usage
#   freesurfer_tables.pl [dir]
#
# Inputs
#   dir is the top-level FreeSurfer output directory containing
#   longitudinal folders, named *.long.* which can exist at any
#   depth beneath dir. Default is the current working directory.
#
# Outputs
#   freesurfer_aseg_vol.csv
#   freesurfer_aparc_vol_right.csv
#   freesurfer_aparc_vol_left.csv
#   freesurfer_aparc_thick_right.csv
#   freesurfer_aparc_thick_left.csv
#   freesurfer_aparc_area_right.csv
#   freesurfer_aparc_area_left.csv
#
# Dependencies
#   - asegstats2table
#   - aparcstats2table
#
# Before running
#   - check all definitions in "system definitions"

#@ DB Clayton - 2019/10/04


# modules
use Cwd qw(getcwd abs_path);
use File::Temp qw(tempfile tempdir);

# system definitions
$aseg = '/opt/freesurfer/bin/asegstats2table';
$aparc = '/opt/freesurfer/bin/aparcstats2table';

# input directory
$ENV{SUBJECTS_DIR} = ($#ARGV < 0) ? getcwd() : abs_path($ARGV[0]);

# output directory
$out = 'tables';
if (-d $out) {
  $out = tempdir('tables_XXXX', DIR=>'.', CLEANUP=>0);
} else {
  mkdir($out);
}

# temporary scan list file
(undef, $scans) = tempfile('scans_XXXX', DIR=>'.', UNLINK=>1);
$opts = "--subjectsfile=$scans --skip -d comma";

# find scan directories
find_scans($scans);

# create tables
print("Writing csv files in directory: $out\n");
system("$aseg $opts -m volume -t $out/freesurfer_aseg_vol.csv");
system("$aparc $opts --hemi rh -m volume -t $out/freesurfer_aparc_vol_right.csv");
system("$aparc $opts --hemi lh -m volume -t $out/freesurfer_aparc_vol_left.csv");
system("$aparc $opts --hemi rh -m thickness -t $out/freesurfer_aparc_thick_right.csv");
system("$aparc $opts --hemi lh -m thickness -t $out/freesurfer_aparc_thick_left.csv");
system("$aparc $opts --hemi rh -t $out/freesurfer_aparc_area_right.csv");
system("$aparc $opts --hemi lh -t $out/freesurfer_aparc_area_left.csv");

# write dictionary
chdir($out);
write_dictionary();

# modify tables
modify_abe();

# done
print("Done!\n");



#
#    SUBROUTINES
#


sub find_scans {

  my(@out, $count, $d);

  print("Finding longitudinal directories...\n");

  @out = `cd $ENV{SUBJECTS_DIR}; find . -type d -name "*\.long\.*"`;

  open(F, "> $_[0]");
  $count = 0;

  for $d (@out) {
    chomp($d);
    $d =~ s/^\.\///;
    if (-f "$d/stats/aseg.stats") {
      print(F "$d\n");
      $count++;
    } else {
      print("Warning: Missing .stats in: $d\n");
    }
  }

  close(F);

  printf("\Summary: %d found, %d skipped, %d processing\n\n", $#out+1, $#out+1-$count, $count);

}


sub modify_abe {

  my($csv, $mod, @list, $study, $x, $err);

  # get Study ID from SUBJECTS_DIR
  if ($ENV{SUBJECTS_DIR} =~ /ABE(4869|4955)g/i) {
    $study = "ABE$1g";
    print("Study ID is: $study\n");
  } else {
    print("Error: Could not determine Study ID from SUBJECTS_DIR: $ENV{SUBJECTS_DIR}\n");
    return;
  }
  
  # list all csv files
  opendir(D, '.');
  @list = grep(/\.csv$/, readdir(D));
  closedir(D);

  # make modified csv files
  for $csv (@list) {
    $csv eq 'freesurfer_dictionary.csv' and next;
    $err = 0;
    $mod = $csv;
    $mod =~ s/^freesurfer/$study/;
    print("Modifying: $csv -> $mod\n");
    open(I, "< $csv");
    open(O, "> $mod");
    while (<I>) {
      if ($. == 1) {
        s/^(.*?),/study,scrnum,visit,/;  # replace first column in header
      } else {
        $x = $_;
        $_ =~ s/^(\d{4})-(\w+)\.long\.BASE,/$study,$1,$2,/;
        $x eq $_ and $err = 1 and last;
      }
      print(O $_);
    }
    close(I);
    close(O);
    if ($err == 1) {
      unlink($mod);
      print("Error: Found line with unexpected format: Did not make new csv\n");
    } else {
      unlink($csv);
    }
  }

}


sub write_dictionary {

  my($method, $label, $region, $hemi, $meas, $unit, %lut_aparc, %lut_aseg, @head, @vars, $v);

  # load DATA into hashes
  while (<DATA>) {
    chomp();
    ($method, $label, $region) = split(':');
    $method eq 'aparc' and $lut_aparc{$label} = $region;
    $method eq 'aseg' and $lut_aseg{$label} = $region;
  }

  # start dictionary with header
  print("Writing: $out/freesurfer_dictionary.csv\n");
  open(D, "> freesurfer_dictionary.csv");
  print(D "VARIABLE,REGION,HEMISPHERE,METHOD,MEASUREMENT,UNIT\n");  # <-- write header

  # get aseg variables from header of csv
  chomp(@head = `head -1 freesurfer_aseg_vol.csv`);
  @vars = split(',', $head[0]);  # split header into variable list
  shift(@vars);  # skip first variable in header

  # process each variable
  for $v (sort(@vars)) {

    if ($v =~ /^(Right-|Left-|lh|rh)(.*)/) {
      ($hemi, $region) = ($1, $2);
      $hemi =~ s/(Right-|rh)/right/;
      $hemi =~ s/(Left-|lh)/left/;
      $region =~ s/-/ /g;
      $region =~ s/^Inf Lat Vent$/Inferior Lateral Ventricle/;
      $region =~ s/^Thalamus Proper$/Thalamus/;
      $region =~ s/^Accumbens area$/Accumbens/;
      $region =~ s/^choroid plexus$/Choroid Plexus/;
      $region =~ s/^VentralDC$/Ventral Diencephalon/;
      $region =~ s/^WM hypointensities$/White Matter Hypointensities/;
      $region =~ s/^non WM hypointensities$/Normal White Matter/;
      $region =~ s/^CerebralWhiteMatterVol$/Cerebral White Matter/;
      $region =~ s/^CortexVol$/Cortical Grey Matter/;
      $region =~ s/^vessel$/Vessel/;
      print(D "$v,$region,$hemi,segmentation,volume,mm3\n");  # <-- write line
      next;
    }

    $region = $lut_aseg{$v};

    if ($region eq '') {
      print("Warning: No aseg region associated with variable: $v\n");
      next;
    }

    $unit = 'volume,mm3';
    $v eq 'BrainSegVol-to-eTIV' and $unit = 'ratio,none';
    $v eq 'MaskVol-to-eTIV' and $unit = 'ratio,none';
    $v eq 'SupraTentorialVolNotVentVox' and $unit = 'count,none';

    print(D "$v,$region,bilateral,segmentation,$unit\n");  # <-- write line

  }

  for $csv (qw(freesurfer_aparc_thick_left.csv freesurfer_aparc_vol_left.csv)) {

    # get aparc variables from header of csv
    chomp(@head = `head -1 $csv`);
    @vars = split(',', $head[0]);  # split header into variable list
    shift(@vars);  # skip first variable in header

    # process each variable
    for $v (sort(@vars)) {

      if ($v =~ /^lh_(.*?)_(thickness|volume)$/) {
        $meas = $2;
        $region = $lut_aparc{$1};
        if ($region eq '') {
          print("Warning: No aparc region associated with variable: $1\n");
          next;
        }
        $unit = ($meas eq 'thickness') ? 'thickness,mm' : 'volume,mm3';
        print(D "$v,$region,left,parcellation,$unit\n");  # <-- write line
        $v =~ s/^lh_/rh_/;
        print(D "$v,$region,right,parcellation,$unit\n");  # <-- write line
        next;
      }

      $v eq 'BrainSegVolNotVent' and next;  # ignore - this is in aseg
      $v eq 'eTIV' and next;  # ignore - this is in aseg

      print("Warning: Unrecognized variable: $v\n");

    }

  }

  close(D);

}


__DATA__

# lines have the format "method:label:region"

# variables that match: /^lh_(.*?)_(thickness|volume)$/

aparc:bankssts:Banks of the Superior Temporal Sulcus
aparc:caudalanteriorcingulate:Caudal Anterior Cingulate
aparc:caudalmiddlefrontal:Caudal Middle Frontal
aparc:cuneus:Cuneus
aparc:entorhinal:Entorhinal
aparc:fusiform:Fusiform
aparc:inferiorparietal:Inferior Parietal
aparc:inferiortemporal:Inferior Temporal
aparc:isthmuscingulate:Isthmus Cingulate
aparc:lateraloccipital:Lateral Occipital
aparc:lateralorbitofrontal:Lateral Orbitofrontal
aparc:lingual:Lingual
aparc:medialorbitofrontal:Medial Orbitofrontal
aparc:middletemporal:Middle Temporal
aparc:parahippocampal:Parahippocampal
aparc:paracentral:Paracentral
aparc:parsopercularis:Pars Opercularis
aparc:parsorbitalis:Pars Orbitalis
aparc:parstriangularis:Pars Triangularis
aparc:pericalcarine:Pericalcarine
aparc:postcentral:Postcentral
aparc:posteriorcingulate:Posterior Cingulate
aparc:precentral:Precentral
aparc:precuneus:Precuneus
aparc:rostralanteriorcingulate:Rostral Anterior Cingulate
aparc:rostralmiddlefrontal:Rostral Middle Frontal
aparc:superiorfrontal:Superior Frontal
aparc:superiorparietal:Superior Parietal
aparc:superiortemporal:Superior Temporal
aparc:supramarginal:Supramarginal
aparc:frontalpole:Frontal Pole
aparc:temporalpole:Temporal Pole
aparc:transversetemporal:Transverse Temporal
aparc:insula:Insula
aparc:MeanThickness:Mean Global Cortex

# variables that do not match: /^(Right-|Left-|lh|rh)(.*)/

aseg:3rd-Ventricle:3rd Ventricle
aseg:4th-Ventricle:4th Ventricle
aseg:5th-Ventricle:5th Ventricle
aseg:CC_Posterior:Posterior Corpus Callosum
aseg:CC_Mid_Posterior:Middle Posterior Corpus Callosum
aseg:CC_Central:Central Corpus Callosum
aseg:CC_Mid_Anterior:Middle Anterior Corpus Callosum
aseg:CC_Anterior:Anterior Corpus Callosum
aseg:SupraTentorialVol:Total Supratentorial Volume
aseg:SupraTentorialVolNotVent:Supratentorial Volume without Ventricles
aseg:SupraTentorialVolNotVentVox:Supratentorial Voxel Count
aseg:BrainSegVol:Segmentation Volume
aseg:BrainSegVolNotVent:Segmentation Volume without Ventricles
aseg:BrainSegVolNotVentSurf:Segmentation Volume without Ventricles from Surf
aseg:WM-hypointensities:White Matter Hypointensities
aseg:non-WM-hypointensities:Normal White Matter
aseg:Brain-Stem:Brain Stem
aseg:CSF:CSF
aseg:Optic-Chiasm:Optic Chiasm
aseg:CortexVol:Cortical Gray Matter
aseg:CerebralWhiteMatterVol:Cerebral White Matter
aseg:SubCortGrayVol:Subcortical Gray Matter
aseg:TotalGrayVol:Total Gray Matter
aseg:MaskVol:Mask Volume
aseg:BrainSegVol-to-eTIV:Ratio of Segmentation Volume to Total Intracranial Volume
aseg:MaskVol-to-eTIV:Ratio of Mask Volume to Total Intracranial Volume
aseg:EstimatedTotalIntraCranialVol:Total Intracranial Volume
