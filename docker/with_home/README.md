

docker build -t aiidalab/qe-tar-home .

docker run --rm -it -p 8888:8888 aiidalab/qe-tar-home



docker run --rm -it aiidalab/qe:amd64-latest /bin/bash



## Error

``` => ERROR [ 4/10] RUN mamba run -n aiida-core-services pg_ctl -w -D /home/jovyan/.postgresql stop                                                                                                      1.7s
------                                                                                                                                                                                                      
 > [ 4/10] RUN mamba run -n aiida-core-services pg_ctl -w -D /home/jovyan/.postgresql stop:                                                                                                                 
1.622 pg_ctl: could not send stop signal (PID: 61): No such process
1.622 
1.622 ERROR conda.cli.main_run:execute(49): `conda run pg_ctl -w -D /home/jovyan/.postgresql stop` failed. (See above for error)
------
Dockerfile:21
--------------------
  19 |     
  20 |     # Stop services for RabbitMQ and PostgreSQL
  21 | >>> RUN mamba run -n aiida-core-services pg_ctl -w -D /home/${NB_USER}/.postgresql stop
  22 |     RUN mamba run -n aiida-core-services rabbitmq-server stop
  23 |     
--------------------
```



```console
$ mamba run -n aiida-core-services rabbitmq-server stop
07:19:34.040 [error] 
07:19:34.047 [error] BOOT FAILED
07:19:34.047 [error] ===========
07:19:34.047 [error] ERROR: distribution port 25672 in use by another node: rabbit@localhost
07:19:34.047 [error] 
07:19:35.048 [error] Supervisor rabbit_prelaunch_sup had child prelaunch started with rabbit_prelaunch:run_prelaunch_first_phase() at undefined exit with reason {dist_port_already_used,25672,"rabbit","localhost"} in context start_error
07:19:35.049 [error] CRASH REPORT Process <0.153.0> with 0 neighbours exited with reason: {{shutdown,{failed_to_start_child,prelaunch,{dist_port_already_used,25672,"rabbit","localhost"}}},{rabbit_prelaunch_app,start,[normal,[]]}} in application_master:init/4 line 138
{"Kernel pid terminated",application_controller,"{application_start_failure,rabbitmq_prelaunch,{{shutdown,{failed_to_start_child,prelaunch,{dist_port_already_used,25672,\"rabbit\",\"localhost\"}}},{rabbit_prelaunch_app,start,[normal,[]]}}}"}

Configuring logger redirection

BOOT FAILED
===========
ERROR: distribution port 25672 in use by another node: rabbit@localhost

Kernel pid terminated (application_controller) ({application_start_failure,rabbitmq_prelaunch,{{shutdown,{failed_to_start_child,prelaunch,{dist_port_already_used,25672,"rabbit","localhost"}}},{rabbit_

Crash dump is being written to: erl_crash.dump...done
```