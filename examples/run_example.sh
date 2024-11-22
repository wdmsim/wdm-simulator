#!/bin/bash

wdmsim run \
	--arbiter example_one_by_one \
	--num_laser_swaps 2 \
	--num_ring_swaps 2 \
	--laser_config_file example_run_config.yaml \
	--ring_config_file example_run_config.yaml \
	--init_lane_order_config_file example_run_config.yaml \
	--tgt_lane_order_config_file example_run_config.yaml \
	--laser_config_section laser-4 \
	--ring_config_section ring-4 \
	--init_lane_order_config_section linear \
	--tgt_lane_order_config_section linear \
	--verbose

