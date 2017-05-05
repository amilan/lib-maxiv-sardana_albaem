# AlbaEM sardana controller

This is the sardanda controller used to control a new EM# from Alba.

## Installation

You can install the sardana controller using one of the following methods:

### Using YUM

If you have configured the MAXIV Laboratory public rpm repository, then it's as
simple as running:

```bash
  sudo yum install sardana-ctrl-albaem
```

### From sources

If you want to install it directly from the sources, the first thing to do is
to get the latest version of the software from [here](https://github.com/amilan/lib-maxiv-sardana_albaem)

You can download it in a zip file or just clone or fork the repository and after
build and install the package.

```bash
  git clone https://github.com/amilan/lib-maxiv-sardana_albaem.git
  cd lib-maxiv-sardana_albaem
  python setup.py install
```

As a last step, ensure that the path where the controller has been installed is
added to the PoolPath property in your Pool.

## Configuration

In order to use the sardana controller, first be sure that you have a Sardana
instance running (either a Sardana or Pool and MacroServer devices running).

Also you need to ensure that you have a Skippy Tango Device Server running and
controlling your EM#. That device server will be the one used by the controller.

For this example, we are going to use spock to define our new controller and its
elements.

So in our example, we will open a new spock session from a terminal, writing:

```bash
  spock --profile=albaem_test
```

With that bash we are going to use a profile called: albaem_test. If this
profile is not existing, it will be created.

### Define a new controller

Once inside spock you can ensure that the albaem is available running the
following macro:

```bash
  lsctrllib
```

AlbaemCoTiCtrl should appear in the list.

After that, you can define a new controller:

```bash
  defctrl AlbaemCoTiCtrl name_of_your_em_ctrl Albaemname name_of_your_skippy_DS
```

And then, you can define the elements like this:
```bash
  defelem name_of_your_em_ti name_of_your_em_ctrl 1
  defelem name_of_your_em_ch1 name_of_your_em_ctrl 2
  defelem name_of_your_em_ch2 name_of_your_em_ctrl 3
  defelem name_of_your_em_ch3 name_of_your_em_ctrl 4
  defelem name_of_your_em_ch4 name_of_your_em_ctrl 5
```

# Troubleshooting

We have seen that sometimes the skippy device server is losing the connection
with the albaem and it's not recovering correctly, causing the tango device
server to be in a non responsive state.

In order to solve this issue, the best practice is to restart the Skippy device
server, and after, the Pool and MacroServer.

## Restarting Skippy

This is the most trickiest part.

Firts, you must log in into the machine were the Skippy DS is running and kill
it manually:

```bash
  ssh user@machine
  ps -ef | grep Skippy
```

It will output the process Id of all the processes with Skippy as a part of its
name. You will need to find the good one and kill it manually:

```bash
  sudo kill -9 process_id
```

And then you are good to restart the Skippy DS, Pool and MacroServer.
