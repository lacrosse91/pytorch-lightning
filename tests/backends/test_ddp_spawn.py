# Copyright The PyTorch Lightning team.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import pytest
import torch

import tests.base.develop_pipelines as tpipes
import tests.base.develop_utils as tutils
from pytorch_lightning.callbacks import EarlyStopping
from pytorch_lightning.core import memory
from pytorch_lightning.trainer import Trainer
from tests.base import BoringModel


@pytest.mark.skipif(torch.cuda.device_count() < 2, reason="test requires multi-GPU machine")
def test_multi_gpu_early_stop_ddp_spawn(tmpdir):
    """Make sure DDP works. with early stopping"""
    class CustomBoringModel(BoringModel):
        def validation_step(self, *args, **kwargs):
            out = super().validation_step(*args, **kwargs)
            self.log('val_loss', out['x'])
            return out

    tutils.set_random_master_port()

    trainer_options = dict(
        default_root_dir=tmpdir,
        callbacks=[EarlyStopping(monitor='val_loss', min_delta=0.1)],
        max_epochs=50,
        limit_train_batches=5,
        limit_val_batches=5,
        gpus=[0, 1],
        accelerator='ddp_spawn',
    )

    model = CustomBoringModel()
    tpipes.run_model_test(trainer_options, model)


@pytest.mark.skipif(torch.cuda.device_count() < 2, reason="test requires multi-GPU machine")
def test_multi_gpu_model_ddp_spawn(tmpdir):
    tutils.set_random_master_port()

    trainer_options = dict(
        default_root_dir=tmpdir,
        max_epochs=1,
        limit_train_batches=10,
        limit_val_batches=10,
        gpus=[0, 1],
        accelerator='ddp_spawn',
        progress_bar_refresh_rate=0,
    )

    model = BoringModel()

    tpipes.run_model_test(trainer_options, model)

    # test memory helper functions
    memory.get_memory_profile('min_max')


@pytest.mark.skipif(torch.cuda.device_count() < 2, reason="test requires multi-GPU machine")
def test_ddp_all_dataloaders_passed_to_fit(tmpdir):
    """Make sure DDP works with dataloaders passed to fit()"""
    tutils.set_random_master_port()

    model = BoringModel()
    fit_options = dict(train_dataloader=model.train_dataloader(),
                       val_dataloaders=model.val_dataloader())

    trainer = Trainer(
        default_root_dir=tmpdir,
        progress_bar_refresh_rate=0,
        max_epochs=1,
        limit_train_batches=0.2,
        limit_val_batches=0.2,
        gpus=[0, 1],
        accelerator='ddp_spawn',
    )
    result = trainer.fit(model, **fit_options)
    assert result == 1, "DDP doesn't work with dataloaders passed to fit()."
