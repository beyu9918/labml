from typing import Any, Dict, List

from fastapi import Request
from labml_db import Model, Index
from labml_db.serializer.pickle import PickleSerializer
from labml_db.serializer.yaml import YamlSerializer

from labml_app.logger import logger
from .distributed_metrics import get_merged_dist_metrics_tracking
from .metrics import get_metrics_tracking
from ..analysis import Analysis
from .. import preferences
from ...db import run


class ComparisonPreferences(preferences.Preferences):
    base_series_preferences: preferences.SeriesPreferences
    base_experiment: str
    is_base_distributed: bool

    @classmethod
    def defaults(cls):
        return dict(base_series_preferences=[],
                    base_experiment=str,
                    step_range=[-1, -1],
                    is_base_distributed=False
                    )

    def update_preferences(self, data: preferences.PreferencesData) -> None:
        if 'base_series_preferences' in data:
            self.update_base_series_preferences(data['base_series_preferences'])

        if 'base_experiment' in data:
            self.base_experiment = data['base_experiment']

        if 'series_preferences' in data:
            self.update_series_preferences(data['series_preferences'])

        if 'chart_type' in data:
            self.chart_type = data['chart_type']

        if 'step_range' in data:
            self.step_range = data['step_range']

        if 'focus_smoothed' in data:
            self.focus_smoothed = data['focus_smoothed']

        r = run.get(self.base_experiment)
        if r is not None and r.world_size > 0:  # distributed run
            self.is_base_distributed = True
        else:
            self.is_base_distributed = False

        self.save()

    def update_base_series_preferences(self, data: preferences.SeriesPreferences) -> None:
        self.base_series_preferences = data

    def get_data(self) -> Dict[str, Any]:
        return {
            'base_series_preferences': self.base_series_preferences,
            'series_preferences': self.series_preferences,
            'base_experiment': self.base_experiment,
            'chart_type': self.chart_type,
            'step_range': self.step_range,
            'focus_smoothed': self.focus_smoothed,
            'is_base_distributed': self.is_base_distributed
        }


@Analysis.db_model(PickleSerializer, 'comparison_preferences')
class ComparisonPreferencesModel(Model['ComparisonPreferencesModel'], ComparisonPreferences):
    pass


@Analysis.db_index(YamlSerializer, 'comparison_preferences_index.yaml')
class ComparisonPreferencesIndex(Index['ComparisonPreferences']):
    pass


@Analysis.route('GET', 'compare/metrics/{run_uuid}')
async def get_comparison_metrics(request: Request, run_uuid: str) -> Any:
    r = run.get(run_uuid)
    if r is None:
        return {}
    if r.world_size == 0:
        return await get_metrics_tracking(request, run_uuid)
    else:  # distributed run
        return await get_merged_dist_metrics_tracking(request, run_uuid)


@Analysis.route('GET', 'compare/preferences/{run_uuid}')
async def get_comparison_preferences(request: Request, run_uuid: str) -> Any:
    preferences_data = {}

    preferences_key = ComparisonPreferencesIndex.get(run_uuid)
    if not preferences_key:
        return preferences_data

    cp: ComparisonPreferences = preferences_key.load()
    preferences_data = cp.get_data()

    return preferences_data


@Analysis.route('POST', 'compare/preferences/{run_uuid}')
async def set_comparison_preferences(request: Request, run_uuid: str) -> Any:
    preferences_key = ComparisonPreferencesIndex.get(run_uuid)

    if not preferences_key:
        cp = ComparisonPreferencesModel()
        ComparisonPreferencesIndex.set(run_uuid, cp.key)
    else:
        cp = preferences_key.load()

    json = await request.json()
    cp.update_preferences(json)

    logger.debug(f'update comparison preferences: {cp.key}')

    return {'errors': cp.errors}
