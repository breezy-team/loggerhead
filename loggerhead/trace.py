#
# Copyright (C) 2008  Canonical Ltd.
#                     (Authored by Martin Albisetti <argentina@gmail.com)
# Copyright (C) 2008  Guillermo Gonzalez <guillo.gonzo@gmail.com>
# Copyright (C) 2006  Robey Pointer <robey@lag.net>
# Copyright (C) 2006  Goffredo Baroncelli <kreijack@inwind.it>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#


def make_handler(config, filename):
    roll = config.get('log.roll', 'never')
    if roll == 'daily':
        h = logging.handlers.TimedRotatingFileHandler(filename, 'midnight', 1, 100)
    elif roll == 'weekly':
        h = logging.handlers.TimedRotatingFileHandler(filename, 'W0', 1, 100)
    else:
        h = logging.FileHandler(filename)
    return h


def setup_logging(log_folder, config, foreground):
    # i hate that stupid logging config format, so just set up logging here.

    if not os.path.exists(log_folder):
        os.mkdir(log_folder)

    f = logging.Formatter('%(levelname)-.3s [%(asctime)s.%(msecs)03d] %(name)s: %(message)s',
                          '%Y%m%d-%H:%M:%S')
    debug_log = make_handler(config, os.path.join(log_folder, 'debug.log'))
    debug_log.setLevel(logging.DEBUG)
    debug_log.setFormatter(f)
    if foreground:
        stdout_log = logging.StreamHandler(sys.stdout)
        stdout_log.setLevel(logging.DEBUG)
        stdout_log.setFormatter(f)
    f = logging.Formatter('[%(asctime)s.%(msecs)03d] %(message)s',
                          '%Y%m%d-%H:%M:%S')
    access_log = make_handler(config, os.path.join(log_folder, 'access.log'))
    access_log.setLevel(logging.INFO)
    access_log.setFormatter(f)

    logging.getLogger('').setLevel(logging.DEBUG)
    logging.getLogger('').addHandler(debug_log)
    logging.getLogger('wsgi').addHandler(access_log)

    if foreground:
        logging.getLogger('').addHandler(stdout_log)