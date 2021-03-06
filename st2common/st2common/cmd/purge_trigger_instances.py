# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""
A utility script that purges trigger instances older than certain
timestamp.

*** RISK RISK RISK. You will lose data. Run at your own risk. ***
"""

from datetime import datetime
import pytz

from mongoengine.errors import InvalidQueryError
from oslo_config import cfg

from st2common import config
from st2common import log as logging
from st2common.script_setup import setup as common_setup
from st2common.script_setup import teardown as common_teardown
from st2common.persistence.trigger import TriggerInstance
from st2common.util import isotime

LOG = logging.getLogger(__name__)
DELETED_COUNT = 0


def _do_register_cli_opts(opts, ignore_errors=False):
    for opt in opts:
        try:
            cfg.CONF.register_cli_opt(opt)
        except:
            if not ignore_errors:
                raise


def _register_cli_opts():
    cli_opts = [
        cfg.StrOpt('timestamp', default=None,
                   help='Will delete trigger instances older than ' +
                   'this UTC timestamp. ' +
                   'Example value: 2015-03-13T19:01:27.255542Z')
    ]
    _do_register_cli_opts(cli_opts)


def purge_trigger_instances(timestamp=None):
    if not timestamp:
        LOG.error('Specify a valid timestamp to purge.')
        return 2

    LOG.info('Purging trigger instances older than timestamp: %s' %
             timestamp.strftime('%Y-%m-%dT%H:%M:%S.%fZ'))

    # XXX: Think about paginating this call.
    query_filters = {'occurrence_time__lt': isotime.parse(timestamp)}
    try:
        TriggerInstance.delete_by_query(**query_filters)
    except InvalidQueryError:
        LOG.exception('Bad query (%s) used to delete trigger instances. ' +
                      'Please contact support.', query_filters)
        return 3
    except:
        LOG.exception('Deleting instances using query_filters %s failed.', query_filters)
        return 4

    # Print stats
    LOG.info('#### Trigger instances deleted.')


def main():
    _register_cli_opts()
    common_setup(config=config, setup_db=True, register_mq_exchanges=False)

    # Get config values
    timestamp = cfg.CONF.timestamp

    if not timestamp:
        LOG.error('Please supply a timestamp for purging models. Aborting.')
        return 1
    else:
        timestamp = datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S.%fZ')
        timestamp = timestamp.replace(tzinfo=pytz.UTC)

    # Purge models.
    try:
        return purge_trigger_instances(timestamp=timestamp)
    finally:
        common_teardown()
