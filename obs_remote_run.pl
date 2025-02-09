#!/usr/bin/perl
use strict;
use warnings;
use XML::LibXML;
use Data::Dumper;
use File::Path qw(make_path rmtree);
use Cwd;
use File::Basename;
use File::Remove 'remove';
use File::Spec::Functions qw(abs2rel catfile catdir);
use IPC::Run3;

# Define the _service file path
my $service_file = '_service';

my @build_mode_functions;
my %source_files;
our $home_directory = getcwd();
our $source_directory = "${home_directory}/.osc.temp/_sources_dir";
our $output_directory = "${home_directory}/.osc.temp/_output_dir";

remove(\1, $output_directory);
remove(\1, $source_directory);

make_path($source_directory);
make_path($output_directory);

{
    my $dir;
    opendir $dir, '.';
    for my $basename (readdir $dir) {
        if (-f $basename) {
            my $dest_file = catfile($source_directory, $basename);
            link($basename, $dest_file);
            $source_files{$basename} = $basename;
        }
    }
    closedir $dir;
}

if (-f $service_file){
    # Create an XML::LibXML object
    my $parser = XML::LibXML->new();

    # Parse the _service file
    my $doc = $parser->parse_file($service_file);

    # Extract information from the _service file
    my $services_node = $doc->documentElement();

    # Iterate over service elements
    foreach my $service_node ($services_node->findnodes('//service')) {
        my $service_name = $service_node->getAttribute('name');
        my $service_mode = $service_node->getAttribute('mode') || 'Default';

        # Extract parameters for each service
        my @params = $service_node->findnodes('.//param');
        my @service_params = ();
        foreach my $param (@params) {
            push @service_params, $param->getAttribute('name'), $param->textContent();
        }
        $service_mode = lc($service_mode);
        # Simulate the actions performed by OBS services based on the mode and parameters
        if ($service_mode eq 'default') {
            # Implement the logic for the 'Default' mode
            RunBefore($service_name)->(@service_params);
        } elsif ($service_mode eq 'trylocal') {
            # Implement the logic for the 'trylocal' mode
            RunBefore($service_name)->(@service_params);
        } elsif ($service_mode eq 'localonly') {
            # Implement the logic for the 'localonly' mode
     #       RunBefore($service_name)->(@service_params);
        } elsif ($service_mode eq 'serveronly') {
            # Implement the logic for the 'serveronly' mode
            RunBefore($service_name)->(@service_params);
        } elsif ($service_mode eq 'buildtime') {
            # Implement the logic for the 'buildtime' mode
            RunAfter($service_name)->(@service_params);
        } elsif ($service_mode eq 'manual') {
            # Implement the logic for the 'manual' mode
        #    manual_mode_action($service_name)->(@service_params);
        } elsif ($service_mode eq 'disabled') {
            # Implement the logic for the 'disabled' mode
        #    disabled_mode_action($service_name)->(@service_params);
        }
    }
}

my $cwd = getcwd();
chdir($output_directory);
while(my($key, $value) = each %source_files) { 
    my $basename = catfile($source_directory, $value);
    link($basename, $key);
    my $ext = substr($value, -8);
  #  print("% $key \n@ $value \n! $ext\n");
    if ($ext eq '.obscpio'){
         #my $extract = Archive::Libarchive::Extract->new( filename => $basename );
         #$extract->extract;
        open( my $input_fh, "<", $basename );
        run3 [qw(cpio -idmu --sparse 
        --no-absolute-filenames 
        --force-local )], $input_fh; 
        close($input_fh);
    }
}
#RunBefore('extract_file')->('archive', '*.obscpio',  'file', '*');
chdir($cwd);

for my $callable (@build_mode_functions){
    $callable->();
}

# # Simulate the action performed in 'Default' mode
# sub default_mode_action {
#     return RunBefore(shift);
# }
#
# # Simulate the action performed in 'trylocal' mode
# sub trylocal_mode_action {
#     return RunBefore(shift);
# }
#
# # Simulate the action performed in 'localonly' mode
# sub localonly_mode_action {
#     return \&manual_mode_action;
# }
#
# # Simulate the action performed in 'serveronly' mode
# sub serveronly_mode_action {
#     return RunBefore(shift);
# }
#
# # Simulate the action performed in 'buildtime' mode
# sub buildtime_mode_action {
#     return RunAfter(shift);
# }
#
# # Simulate the action performed in 'manual' mode
# sub manual_mode_action {
#     return \&manual_mode_action;
# }
#
# # Simulate the action performed in 'disabled' mode
# sub disabled_mode_action {
#     return \&manual_mode_action;
# }

sub Run {
    my ($cwd_rel, $outdir_rel, $service_name, $final_func) = @_;
 #   my $cwd = Cwd::realpath($cwd_rel);
 #   my $outdir = Cwd::realpath($outdir_rel);
    make_path($outdir_rel);
    return sub  {
        my $pid = fork;
        if ($pid == 0){
            my $path = "/usr/lib/obs/service/$service_name";
            my @args;
            loop0:
            my $name = shift;
            my $value = shift;
            if (defined($name)){
                push @args, "--$name";
                push @args, "$value";
                goto loop0;
            }
            my $outdir_rel = abs2rel($outdir_rel, $cwd_rel);

            print "\n______RUN______\ncd $cwd_rel ; mkdir -p $outdir_rel ; $path --outdir $outdir_rel ", join(' ', @args), " ; \n";
            chdir $cwd_rel;
            exec($path, '--outdir', $outdir_rel, @args);
        } else {
            waitpid($pid, 0);
            if (defined($final_func)){
                &$final_func($cwd_rel, $outdir_rel, $service_name);
            }
            print("\n______END______\n");
        }
    }
}

sub random {
    my $foo = '';
    $foo .= sprintf("%x", rand 16) for 1..8;
    return $foo;
}

sub RunBefore {
   my ($name, $source, $suffix) = @_;
   if (! defined($suffix)){
     $suffix = "_service:$name:";
   };
   if (! defined($source)){
     $source = $source_directory;
   };
   my $uuid = random();
   my $outdir = "${home_directory}/.osc.temp/_tmp_dir/_service.$name.$uuid";
   make_path($outdir);
   return Run($source, $outdir, $name, sub{
      my ($cwd, $outdir, $service_name) = @_;
      my $dir;
      opendir $dir, $outdir;
      for my $basename (readdir $dir) {
          my $path = catfile($outdir, $basename);
          if (-f $path) {
              my $sername = "${suffix}${basename}";
              my $dest_file = catfile($cwd, $sername);
              $source_files{$basename} = $sername;
              unlink($dest_file);
              link($path, $dest_file);
          }
      };
      closedir $dir;
   });
}

sub RunAfter {
    my $service_name = shift;
    return sub {
        my @args = @_;
        push @build_mode_functions, sub{
            our $output_directory;
            return RunBefore($service_name, 
                $output_directory, "")->(@args);
        };
    };
}

