import subprocess
import os
import requests
import logging

queue = []
sliced = []

logger = logging.getLogger('pront')

def process_queue(slic3r, config):
    for item in queue:
        logger.debug("Fetching " + item['url'] + ', allowing redirects')
        item_path = '/tmp/' + str(hash(item['url'])) + '.stl'

        with requests.get(item['url'], allow_redirects=True, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:47.0) Gecko/20100101 Firefox/47.0'}) as r:
            with open(item_path, 'wb') as f:
                logger.debug("Saving to " + item_path)
                f.write(r.content)

        command_string = [str(slic3r), "--load ", str(config), " --output", item_path + ".gcode ", item_path]
        logger.debug("Slic3r command: " + str(command_string))
        result = subprocess.run(command_string, stdout=subprocess.PIPE)
        logger.debug(result.stdout)

        os.remove(item_path)

        queue.remove(item)

    pass

