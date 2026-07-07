API reference
=============

All public functions are re-exported from the top-level :mod:`trilatmoor`
package, so ``from trilatmoor import <name>`` works for every symbol listed
here.

.. contents:: Modules
   :local:
   :depth: 1


Parsing — ``read_dship``
------------------------

.. automodule:: trilatmoor.read_dship
   :members:
   :undoc-members: False
   :show-inheritance:


Solving — ``solve_anchor``
--------------------------

.. automodule:: trilatmoor.solve_anchor
   :members:
   :undoc-members: False
   :show-inheritance:


Plotting — ``plotting``
-----------------------

.. automodule:: trilatmoor.plotting
   :members: plot_trilateration_survey, plot_multiple_surveys,
             plot_multiple_solutions, plot_survey_grid,
             load_bathymetry_netcdf, load_bathymetry_netcdf_subsampled,
             load_ship_track_netcdf,
             query_depth_at_position,
             process_survey_file, parse_survey_file,
             save_cropped_figure
   :undoc-members: False
   :show-inheritance:


Utilities — ``utilities``
-------------------------

.. automodule:: trilatmoor.utilities
   :members:
   :undoc-members: False
   :show-inheritance:


CLI — ``cli``
-------------

.. automodule:: trilatmoor.cli
   :members: process_single_survey, process_multiple_surveys,
             write_anchor_position_file
   :undoc-members: False
   :show-inheritance:
