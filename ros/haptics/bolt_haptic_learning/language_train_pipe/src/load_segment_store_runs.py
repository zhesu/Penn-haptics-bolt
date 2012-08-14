#!/usr/bin/env python

# Script to start loading data into pytables and convert into meaningful features
import roslib; roslib.load_manifest("language_train_pipe")
import rospy
import sys
import tables
import numpy as np
import cPickle

from bolt_pr2_motion_obj import BoltPR2MotionObj

# Pulls out the data for a segment from a run
def PullDataFromRun(one_run_pytable_ptr, pull_state):
    
    # pull out controller state array
    state_array = one_run_pytable_ptr.state.controller_state[:]
    # Get index into the array that matches the state 
    idx_segment = np.nonzero(state_array == pull_state)

    # Create PR2MotionObj
    motion_object = BoltPR2MotionObj()

    # Store the state in the object
    motion_object.state = pull_state

    # Get the name of the current file and parse
    object_full_name = one_run_pytable_ptr._v_name
    object_name_split = object_full_name.split('_')
    object_run_num = object_name_split[-1] 
    object_name = "_".join(object_name_split[0:-1])

    # Store parsed info
    motion_object.name = object_name
    motion_object.run_number = int(object_run_num)

    # Create list to store the values before converting into numpy array
    electrodes = []
    tdc = []
    tac = []
    pac = []
    pac_flat = []
    pdc = []

    # Biotac information
    for _finger in xrange(one_run_pytable_ptr.biotacs._v_depth):

        # Create name to eval for finger
        finger_name_list = [] 
        finger_name_list.append('one_run_pytable_ptr.biotacs.finger_')
        finger_name_list.append(str(_finger))

        finger_name = ''.join(finger_name_list)

        # Electrodes
        one_set_electrode = eval(finger_name + '.electrodes[:]')
        one_motion_electrode = one_set_electrode[idx_segment]
        electrodes.append(one_motion_electrode)

        # TDC
        one_set_tdc = eval(finger_name + '.tdc[:]')
        one_motion_tdc = one_set_tdc[idx_segment]
        tdc.append(one_motion_tdc)

        # TAC
        one_set_tac = eval(finger_name + '.tac[:]')
        one_motion_tac = one_set_tac[idx_segment]
        tac.append(one_motion_tac)

        # PDC
        one_set_pdc = eval(finger_name + '.pdc[:]')
        one_motion_pdc = one_set_pdc[idx_segment]
        pdc.append(one_motion_pdc)

        # PAC
        one_set_pac_flat = eval(finger_name + '.pac[:]')
        one_motion_pac_flat = one_set_pac_flat[idx_segment]
        pac.append(one_motion_pac_flat)

        # PAC FLAT
        pac_flat.append(one_motion_pac_flat.reshape(1, len(one_motion_pac_flat)*22)[0])
   
    # Store biotac into object
    motion_object.electrodes = np.array(electrodes)
    motion_object.tdc = np.array(tdc)
    motion_object.tac = np.array(tac)
    motion_object.pdc = np.array(pdc)
    motion_object.pac = np.array(pac)
    motion_object.pac_flat = np.array(pac_flat)

    # Store gripper information
    # Velocity 
    gripper_velocity = one_run_pytable_ptr.gripper_aperture.joint_velocity[:] 
    motion_object.gripper_velocity = gripper_velocity[idx_segment]
   
    # Position
    gripper_position = one_run_pytable_ptr.gripper_aperture.joint_position[:] 
    motion_object.gripper_position = gripper_position[idx_segment]

    # Motor Effort
    gripper_effort = one_run_pytable_ptr.gripper_aperture.joint_effort[:] 
    motion_object.gripper_effort = gripper_effort[idx_segment]

    # Store accelerometer
    accelerometer = one_run_pytable_ptr.accelerometer[:] 
    motion_object.accelerometer = accelerometer[idx_segment]

    return motion_object


def main():

    # Parse out the arguments passed in 
    if len(sys.argv) < 3:
        raise Exception("Usage: %s [input_file] [output_file]", sys.argv[0])

    input_filename = sys.argv[1]
    output_filename = sys.argv[2]

    if not input_filename.endswith(".h5"):
        raise Exception("Input file is %s \nPlease pass in a hdf5 data file" % input_filename)

    if not output_filename.endswith(".pkl"):
        output_filename = output_filename + '.pkl'

    # Load the data from an h5 file
    all_data = tables.openFile(input_filename)

    # Create a storage container for data
    tap_runs = list()
    squeeze_runs = list()
    hold_runs = list() 
    slow_slide_runs = list()
    fast_slide_runs = list()

    # Create dictonary to store the final lists
    segmented_data = dict()

    # Keep counter of the number of runs done
    num_runs = 0

    # Pull pointers to only the file heads of the data structure
    all_runs_root = [_g for _g in all_data.walkGroups("/") if _g._v_depth == 1]

    # For each file extract the segments and data
    for _objectRun in all_runs_root:
        num_runs += 1
        print num_runs

        # Pull out tap information
        tap_object = PullDataFromRun(_objectRun, BoltPR2MotionObj.TAP)
        tap_runs.append(tap_object)

        # Pull out squeeze information
        squeeze_object = PullDataFromRun(_objectRun, BoltPR2MotionObj.SQUEEZE)
        squeeze_runs.append(squeeze_object)

        # Pull out hold information
        hold_object = PullDataFromRun(_objectRun, BoltPR2MotionObj.THERMAL_HOLD) 
        hold_runs.append(hold_object)

        # Pull out slide fast information
        slide_fast_object = PullDataFromRun(_objectRun, BoltPR2MotionObj.SLIDE_FAST)
        fast_slide_runs.append(slide_fast_object)

        # Pull out slide slow information
        slide_slow_object = PullDataFromRun(_objectRun, BoltPR2MotionObj.SLIDE)
        slow_slide_runs.append(slide_slow_object)
   

    # Store all of the lists into the dictionary
    segmented_data['tap'] = tap_runs
    segmented_data['squeeze'] = squeeze_runs
    segmented_data['thermal_hold'] = hold_runs
    segmented_data['slide'] = slow_slide_runs
    segmented_data['slide_fast'] = fast_slide_runs

    file_ptr = open(output_filename, "w")
    cPickle.dump(segmented_data, file_ptr, cPickle.HIGHEST_PROTOCOL)
    file_ptr.close()

if __name__== "__main__":
    main()

