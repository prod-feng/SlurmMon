Rocky Linux 9.x, slurm23.02, singularity-ce-4.3.1.

Singularity/apptainer image to run Django web based HPC Slurm resource and configuration monitoring.

# 1

```
git clone ttps://github.com/prod-feng/SlurmMon/

cd SlurmMon

```

Make a image use the def file in appraiser/ folder.

# 2
run command:

```

./run_me.sh start

./run_me.sh status

./run_me.sh stop
```

to start the container.


Modify the run\_me.sh to set up the Bind port and IP according to your needs.


<img width="953" height="678" alt="Screenshot-SlurmMon" src="https://github.com/user-attachments/assets/393754fa-321f-408e-8ebf-d40b7ad4e771" />
