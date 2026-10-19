"""v18: one bounded, certified short route to an inherited accepted endpoint.

This changes the finite endpoint family, not IK convergence tolerances. All
geometry, sequential IK, work, time and live-execution contracts are inherited.
There are still four candidates: the unused 30-degree center alternative is
replaced, rather than adding unbounded fallback attempts.
"""
import numpy as np
from reproduction.improvement_v15_20261016_01.recovery.carry_path import _stage
from reproduction.improvement_v16_20261016_01.recovery.carry_search import (
    REGION_INSET_M, PLACE_HEIGHT_M,
)
from reproduction.improvement_v17_20261019_01.recovery.carry_search import (
    CarryPathSearch as V17Search,
)


class CarryPathSearch(V17Search):
    """Same constructor, advance API and guarded chosen-route schema as v17.

    The new route retains the original requested orientation. Its carried-can
    center is 35 mm toward the fixed robot base, and its placement center is
    floor + 95 mm, both already used by v16's inset alternatives. The observed
    rigid hand-can transform determines the exact hand targets. Every mixed
    transport and placement sample must pass the unchanged certificates.

    preserve_current is always False: the controller must execute these exact
    goals with its original five-frame arrival and live grasp/joint/geometry
    guards. No case identifier, task outcome or future observation is used.
    """
    def _start_option(self):
        if not self._ordered:
            radial = np.array([-.5, -.1])-self.target[:2]
            radial /= max(float(np.linalg.norm(radial)), 1e-12)
            inset = self.target[:2]+REGION_INSET_M*radial
            self.options = [
                ('current_rotation_inset', self.original_rotation.copy(),
                 inset.copy(), self.floor+PLACE_HEIGHT_M)
                if option[0] == 'outward_30_center' else option
                for option in self.options
            ]
            assert len(self.options) == 4
        super()._start_option()
        name = self.options[self.index][0]
        self.receipt.update(
            short_original_route=name == 'current_exact',
            short_verified_route=bool(self.short_route),
            endpoint_family='inherited_inset_original_rotation' if name == 'current_rotation_inset' else 'v17_original_family',
            endpoint_change_is_not_pure_ik_repair=name == 'current_rotation_inset',
        )

    def _route(self, option):
        route = super()._route(option)
        if option[0] == 'current_rotation_inset':
            route['stages'] = [_stage(
                'direct_transport', 'translate', self.x[:3].copy(),
                route['stages'][-1]['goal'].copy(), self.start_rotation.copy(),
                route['rotation'].copy(),
            )]
            route['short'] = True
        return route

    def _finish_option(self, reason, accepted=False):
        receipt = self.receipt
        super()._finish_option(reason, accepted)
        if receipt['accepted']:
            self.chosen.update(
                short_original_route=receipt['short_original_route'],
                short_verified_route=receipt['short_verified_route'],
                endpoint_family=receipt['endpoint_family'],
                endpoint_change_is_not_pure_ik_repair=receipt['endpoint_change_is_not_pure_ik_repair'],
            )
