import os
import sys
import argparse
from modules import logger
from modules import configuration
from pathlib import Path
from modules.CustomConfigParser import CustomConfigParser
from modules.TerraformController import TerraformController
import colorama
from colorama import Fore, Back, Style

colorama.init(autoreset=True)



# need to set this ENV var due to a OSX High Sierra forking bug
# see this discussion for more details: https://github.com/ansible/ansible/issues/34056#issuecomment-352862252
os.environ['OBJC_DISABLE_INITIALIZE_FORK_SAFETY'] = 'YES'

VERSION = 1


def init(args):
    config = args.config
    print(Back.BLACK + Fore.GREEN + """
starting program loaded for B1 battle droid """ + Back.BLACK + Fore.BLUE + Style.BRIGHT + """
          ||/__'`.
          |//()'-.:
          |-.||
          |o(o)
          |||\\\  .==._
          |||(o)==::'
           `|T  ""
            ()
            |\\
            ||\\
            ()()
            ||//
            |//
           .'=`=.
    """)

    # parse config
    attack_range_config = Path(config)
    if attack_range_config.is_file():
        print(Back.BLACK + Fore.GREEN + "attack_range is using config at path " + Style.BRIGHT + "{0}".format(
            attack_range_config))
        configpath = str(attack_range_config)
    else:
        print("ERROR: attack_range failed to find a config file")
        sys.exit(1)

    # Parse config
    parser = CustomConfigParser()
    config = parser.load_conf(configpath)

    log = logger.setup_logging(config['log_path'], config['log_level'])
    log.info("INIT - attack_range v" + str(VERSION))

    if config['cloud_provider'] == 'azure':
        os.environ["AZURE_SUBSCRIPTION_ID"] = config['azure_subscription_id']

    if config['attack_range_password'] == 'Pl3ase-k1Ll-me:p':
        log.error('ERROR: please change attack_range_password in attack_range.conf')
        sys.exit(1)

    if config['cloud_provider'] == 'azure' and config['zeek_sensor'] == '1':
        log.error('ERROR: zeek sensor only available for aws in the moment. Plase change zeek_sensor to 0 and try again.')
        sys.exit(1)

    if config['cloud_provider'] == 'aws' and config['windows_client'] == '1':
        log.error('ERROR: windows client is only support for Azure.')
        sys.exit(1)

    return TerraformController(config, log), config, log


def configure(args):
    configuration.new(args.config)

def show(args):
    controller, _, _ = init(args)
    if args.machines:
        controller.list_machines()


def simulate(args):
    controller, config, _ = init(args)
    target = args.target
    simulation_techniques = args.simulation_technique
    simulation_atomics = args.simulation_atomics
    # lets give CLI priority over config file for pre-configured techniques
    if simulation_techniques:
        pass
    else:
        simulation_techniques = config['art_run_techniques']

    if not simulation_atomics:
        simulation_atomics = 'no'
    return controller.simulate(target, simulation_techniques, simulation_atomics)

def dump(args):
    controller, _, _ = init(args)
    controller.dump_attack_data(args.dump_name, args.last_sim)


def replay(args):
    controller, _, log = init(args)
    controller.replay_attack_data(args.dump_name, args.dump)


def build(args):
    controller, _, _ = init(args)
    controller.build()


def destroy(args):
    controller, _, _ = init(args)
    controller.destroy()


def stop(args):
    controller, _, _ = init(args)
    controller.stop()


def resume(args):
    controller, _, _ = init(args)
    controller.resume()


def test(args):
    controller, _, _ = init(args)
    # split the comma delimted list
    tests = args.test_files.split(",")
    return controller.test(tests, args.test_build_destroy, args.test_delete_data)


def main(args):
    # grab arguments
    parser = argparse.ArgumentParser(
        description="Use `attack_range.py action -h` to get help with any Attack Range action")
    parser.add_argument("-c", "--config", required=False, default="attack_range.conf",
                        help="path to the configuration file of the attack range")
    parser.add_argument("-v", "--version", default=False, action="version", version="version: {0}".format(VERSION),
                        help="shows current attack_range version")
    parser.set_defaults(func=lambda _: parser.print_help())

    actions_parser = parser.add_subparsers(title="attack Range actions", dest="action")
    configure_parser = actions_parser.add_parser("configure", help="configure a new attack range")
    build_parser = actions_parser.add_parser("build", help="builds attack range instances")
    simulate_parser = actions_parser.add_parser("simulate", help="simulates attack techniques")
    destroy_parser = actions_parser.add_parser("destroy", help="destroy attack range instances")
    stop_parser = actions_parser.add_parser("stop", help="stops attack range instances")
    resume_parser = actions_parser.add_parser("resume", help="resumes previously stopped attack range instances")
    show_parser = actions_parser.add_parser("show", help="list machines")
    test_parser = actions_parser.add_parser("test", help="test detections")
    dump_parser = actions_parser.add_parser("dump", help="dump locally logs from attack range instances")
    replay_parser = actions_parser.add_parser("replay", help="replay dumps into the splunk server")

    # Build arguments
    build_parser.set_defaults(func=build)

    # Destroy arguments
    destroy_parser.set_defaults(func=destroy)

    # Stop arguments
    stop_parser.set_defaults(func=stop)

    # Resume arguments
    resume_parser.set_defaults(func=resume)

    # Configure arguments
    configure_parser.add_argument("-c", "--config", required=False, type=str, default='attack_range.conf',
                                    help="provide path to write configuration to")
    configure_parser.set_defaults(func=configure)

    # Simulation arguments
    simulate_parser.add_argument("-t", "--target", required=True,
                                 help="target for attack simulation. Use the name of the aws EC2 name")
    simulate_parser.add_argument("-st", "--simulation_technique", required=False, type=str, default="",
                                 help="comma delimited list of MITRE ATT&CK technique ID to simulate in the "
                                      "attack_range, example: T1117, T1118, requires --simulation flag")
    simulate_parser.add_argument("-sa", "--simulation_atomics", required=False, type=str, default="",
                                 help="specify dedicated Atomic Red Team atomics to simulate in the attack_range, "
                                      "example: Regsvr32 remote COM scriptlet execution for T1117")
    simulate_parser.set_defaults(func=simulate)

    # Dump  Arguments
    dump_parser.add_argument("-dn", "--dump_name", required=True,
                             help="name for the dumped attack data")
    dump_parser.add_argument("--last-sim", required=False, action='store_true',
                             help="overrides dumps.yml time and dumps from the start of previous simulation")
    dump_parser.set_defaults(func=dump)

    # Replay Arguments
    replay_parser.add_argument("-dn", "--dump_name", required=True,
                               help="name for the data dump folder under attack_data/")
    replay_parser.add_argument("--dump", required=False,
                        help="name of the data dump as defined in attack_data/dumps.yml")
    replay_parser.set_defaults(func=replay)

    # Test Arguments
    test_parser.add_argument("-tf", "--test_files", required=True,
                             type=str, default="", help='comma delimited list relative path of the test files')
    test_parser.add_argument("-tbd", "--test_build_destroy", required=False, default=False,
                             action="store_true", help='builds a attack_range, then runs the test files and finally destroy the range in one shot operation.')
    test_parser.add_argument("-tdd", "--test_delete_data", required=False, default=False,
                             action="store_true", help='delete the replayed attack data after detection test.')
    test_parser.set_defaults(func=test, test_build_destroy=False)

    # Show arguments
    show_parser.add_argument("-m", "--machines", required=False, default=False,
                             action="store_true", help="prints out all available machines")
    show_parser.set_defaults(func=show, machines=True)

    # # parse them
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    main(sys.argv[1:])
