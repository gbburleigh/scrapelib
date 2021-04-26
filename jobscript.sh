#!/bin/bash
#SBATCH -A kellogg               # Allocation
#SBATCH -p normal                # Queue
#SBATCH -t 48:00:00             # Walltime/duration of the job
#SBATCH -N 1                    # Number of Nodes
#SBATCH --mem=18G               # Memory per node in GB needed for a job. Also see --mem-per-cpu
#SBATCH --ntasks-per-node=6     # Number of Cores (Processors)
#SBATCH --mail-user=grahamburleigh2022@u.northwestern.edu  # Designate email address for job communications
#SBATCH --mail-type=BEGIN,FAIL,END     # Events options are job BEGIN, END, NONE, FAIL, REQUEUE
#SBATCH --job-name="upwork_fullscan"       # Name of job

# unload any modules that carried over from your command line session
module purge

# add a project directory to your PATH (if needed)
export PATH=$PATH:/projects/kellogg/gbb5412/scrapelib

# load modules you need to use
module load python/anaconda

source scrape-env/bin/activate

python3 driver.py -r -p -full