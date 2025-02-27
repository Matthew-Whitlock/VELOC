#!/usr/bin/env python3

import sys, os.path, shutil, subprocess
import argparse
import re
import tarfile

# CRAY-specific compiler options
# compiler_options = ["-DCMAKE_C_COMPILER=cc", "-DCMAKE_C_FLAGS=-dynamic", "-DCMAKE_CXX_COMPILER=CC", "-DCMAKE_CXX_FLAGS=-dynamic"]
compiler_options = []
cmake_build_type="Release"

def install_dep(git_link, dep_vers, pkg_options = ["-DENABLE_TESTS=OFF"]):
    name = os.path.basename(git_link).split('.')[0]
    print("Installing {0}...".format(name))
    try:
        tmp_dir = args.temp + '/' + name
        subprocess.call(["git", "clone", "-b", dep_vers, "--depth", "1", git_link, tmp_dir])
        cmake_args = ["-DCMAKE_INSTALL_PREFIX=" + args.prefix, "-DCMAKE_BUILD_TYPE=" + cmake_build_type] + compiler_options + pkg_options
        subprocess.check_call(["cmake"] + cmake_args, cwd=tmp_dir)
        subprocess.check_call(["cmake", "--build", tmp_dir, '--target', 'install'])
    except Exception as err:
        print("Error installing dependency {0}: {1}!".format(git_link, err))
        sys.exit(4)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='VeloC installation script')
    parser.add_argument('--protocol', default='socket_queue',
                        help='communication protocol between client and active backend (default: socket_queue). Only for advanced users.')
    parser.add_argument('--posix-io', default='direct',
                        help='POSIX transfer method between scratch and persistent (default: direct, alternative: rw).')
    parser.add_argument('--without-boost', action='store_true',
                        help='use existing Boost libraries for ipc_queue protocol (assume pre-installed)')
    parser.add_argument('--without-deps', action='store_true',
                        help='use existing component libraries (assume pre-installed)')
    parser.add_argument('--debug', action='store_true',
                        help='build debug and keep temp directory')
    parser.add_argument('--temp', default='/tmp/veloc',
                        help='temporary directory used during the install (default: /tmp/veloc)')
    parser.add_argument('prefix',
                        help='installation path prefix (typically a home directory)')
    parser.add_argument('extra_cmake_args', nargs='*',
                        help='additional cmake arguments to pass to configure')
    args = parser.parse_args()
    args.prefix = os.path.abspath(args.prefix)
    if not os.path.isdir(args.prefix):
        print("Installation prefix {0} is not a valid directory!".format(args.prefix))
        sys.exit(1)
    if os.path.isdir(args.temp):
        print("Installation temporary directory {0} already exists, please remove and/or specify a different one!".format(args.temp))
        sys.exit(2)
    try:
         os.mkdir(args.temp)
    except OSError as err:
        print("Cannot create temporary directory {0}!".format(args.temp))
        sys.exit(3)

    print("Installing VeloC in {0}...".format(args.prefix))

    if (args.debug):
        cmake_build_type="Debug"
    compiler_options = compiler_options + args.extra_cmake_args;

    # Boost
    if (args.protocol == "ipc_queue" and not args.without_boost):
        print("Downloading Boost...")
        import wget, bs4, urllib
        try:
            req = urllib.request.Request('https://www.boost.org/users/download', headers={'User-Agent': 'Mozilla/5.0'})
            soup = bs4.BeautifulSoup(urllib.request.urlopen(req), 'html.parser')
            link_list = soup.findAll('a', attrs={'href': re.compile("bz2")})
            if len(link_list) > 0:
                boost_arch = wget.download(link_list[0].get('href'), out=args.temp)
                f = tarfile.open(boost_arch, mode='r:bz2')
                f.extractall(path=args.temp)
                f.close()
                shutil.move(args.temp + '/' + os.path.basename(boost_arch).split('.')[0]
                            + '/boost', args.prefix + '/include/boost')
        except Exception as err:
            print("Error installing Boost: {0}! Try to install it manually and use --without-boost. Alternatively, use --protocol=socket_queue".format(err))
            sys.exit(3)

    # Other dependencies
    if (not args.without_deps):
        install_dep('https://github.com/ECP-VeloC/KVTree.git', 'v1.4.0')
        install_dep('https://github.com/ECP-VeloC/AXL.git', 'v0.8.0')
        install_dep('https://github.com/ECP-VeloC/rankstr.git', 'v0.3.0')
        install_dep('https://github.com/ECP-VeloC/shuffile.git', 'v0.3.0')
        install_dep('https://github.com/ECP-VeloC/redset.git', 'v0.3.0')
        install_dep('https://github.com/ECP-VeloC/er.git', 'v0.4.0')

    # VeloC
    veloc_build = './build'
    try:
        if (os.path.isdir(veloc_build)):
            shutil.rmtree(veloc_build)
        os.mkdir(veloc_build)
    except OSError as err:
        print("Cannot create build directory {0}!".format(veloc_build))
        sys.exit(2)

    # Construct the fulls et of CMake arguments
    cmake_args= ['-DCMAKE_INSTALL_PREFIX='+args.prefix,
                 '-DCMAKE_BUILD_TYPE='+cmake_build_type,
                 '-DCOMM_QUEUE='+args.protocol,
                 '-DPOSIX_IO='+args.posix_io] + compiler_options
    # Configure
    print("CMake arguments: " + " ".join(cmake_args))
    ret = subprocess.call(['cmake'] + cmake_args + [os.getcwd()], cwd=veloc_build,)
    # Build and install
    if ret == 0:
        ret = subprocess.call(['cmake', '--build', veloc_build, '--target', 'install'])

    # Cleanup
    if (not args.debug):
        try:
            shutil.rmtree(args.temp)
        except OSError as err:
            print("Cannot cleanup temporary directory {0}!".format(args.temp))
            sys.exit(4)

    if ret == 0:
        print("Installation successful!")
    else:
        print("Installation failed!")
        sys.exit(ret)
