# Shake&Tune: 3D printer analysis tools
#
# Copyright (C) 2024 Félix Boisselier <felix@fboisselier.fr> (Frix_x on Discord)
# Licensed under the GNU General Public License v3.0 (GPL-3.0)
#
# File: shaper_graph_creator.py
# Description: Input shaper graph creator implementation

import json
from typing import Any, Optional

from ..helpers.accelerometer import MeasurementsManager
from ..helpers.console_output import ConsoleOutput
from ..shaketune_config import ShakeTuneConfig
from .computations.shaper_computation import ShaperComputation
from .graph_creator import GraphCreator
from .plotters.shaper_plotter import ShaperPlotter


@GraphCreator.register('input shaper')
class ShaperGraphCreator(GraphCreator):
    """Input shaper graph creator using composition-based architecture"""

    def __init__(self, config: ShakeTuneConfig):
        super().__init__(config, ShaperComputation, ShaperPlotter)
        self._max_smoothing: Optional[float] = None
        self._scv: float = 5.0  # Default square corner velocity
        self._test_params: Optional[Any] = None
        self._max_scale: Optional[float] = None
        self._profile: str = 'lowvibr'  # Which recommended filter to export ('lowvibr' or 'performance')

    def configure(
        self,
        scv: float = 5.0,
        max_smoothing: Optional[float] = None,
        test_params: Optional[Any] = None,
        max_scale: Optional[float] = None,
        profile: str = 'lowvibr',
    ) -> None:
        """Configure the input shaper parameters"""
        self._scv = scv
        self._max_smoothing = max_smoothing
        self._test_params = test_params
        self._max_scale = max_scale
        self._profile = profile

    def _export_results(self, result) -> None:
        """Write the recommended input shaper filter to a sidecar JSON file.

        Runs inside the Shake&Tune child process. The main Klipper process reads this
        file back (next to the output target) to apply and persist the filter in printer.cfg.
        """
        if self._output_target is None:
            return

        # shaper_choices[0] is always Klipper's recommendation (the low-vibration one shown
        # in cyan on the graph). shaper_choices[1], when present, is the "performance" one.
        choices = result.shaper_choices
        if self._profile == 'performance' and len(choices) > 1:
            chosen = choices[1]
        else:
            chosen = choices[0]

        shaper_info = next(
            (s for s in result.shaper_table_data['shapers'] if s['type'] == chosen),
            None,
        )
        if shaper_info is None:
            return

        profile_data = {
            'shaper_type': shaper_info['type'].lower(),
            'shaper_freq': round(float(shaper_info['frequency']), 1),
            'damping_ratio': round(float(result.zeta), 3),
        }

        try:
            with open(self._output_target.with_suffix('.shaper.json'), 'w') as f:
                json.dump(profile_data, f)
        except OSError as e:
            ConsoleOutput.print(f'Warning: failed to export the input shaper profile: {e}')

    def _create_computation(self, measurements_manager: MeasurementsManager) -> ShaperComputation:
        """Create the computation instance with proper configuration"""
        return ShaperComputation(
            measurements=measurements_manager.get_measurements(),
            max_smoothing=self._max_smoothing,
            scv=self._scv,
            max_freq=self._config.max_freq,
            test_params=self._test_params,
            max_scale=self._max_scale,
            st_version=self._version,
        )
