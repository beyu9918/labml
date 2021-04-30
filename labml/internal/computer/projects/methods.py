from typing import List

from labml.internal.computer.configs import computer_singleton
from labml.internal.computer.projects.sync import SyncRuns
from labml.internal.manage.tensorboard import TensorBoardStarter

SYNC_RUNS = SyncRuns()
TENSORBOARD_STARTER = TensorBoardStarter(
    computer_singleton().tensorboard_symlink_dir,
    computer_singleton().tensorboard_port,
    computer_singleton().tensorboard_visible_port,
    computer_singleton().tensorboard_protocol,
    computer_singleton().tensorboard_host,
)


def start_tensorboard(*, runs: List[str]):
    paths = [r.path for r in SYNC_RUNS.get_runs(runs)]
    if TENSORBOARD_STARTER.start(paths):
        return {'url': TENSORBOARD_STARTER.url}
    else:
        return {}


def delete_runs(*, runs: List[str]):
    return 'deleted'


def clear_checkpoints(*, runs: List[str]):
    return 'deleted'


def call_sync():
    SYNC_RUNS.sync()
    return {'synced': True}


METHODS = {
    'start_tensorboard': start_tensorboard,
    'delete_runs': delete_runs,
    'clear_checkpoints': clear_checkpoints,
    'call_sync': call_sync,
}
