# Import standard libraries.
import time
import sys

# Import external libraries.
import awkward as ak
import pika
import pickle
import uproot
import vector

# Import local modules.
import comms
import config
import infofile


def main():
    """
    Represents a worker node that processes batches of data received from a 
    manager node. The data should be data for the Higgs to 4-Lepton decay 
    process from the ATLAS Open Data project. The worker node terminates if 
    there are no more messages left in the RabbitMQ queue.
    """

    # Open a connection to the RabbitMQ server.
    connection = comms.open_connection(comms.RABBITMQ_SERVER, retries=6, wait_time=5)

    # If a connection cannot be established.
    if connection is None:
        # Print an error message and terminate the program.
        print("error: RabbitMQ connection failed")
        sys.exit(1)

    # Open a channel and declare the queue.
    channel = connection.channel()
    channel.queue_declare(comms.TASKS_QUEUE)

    # Retrieve and process batches of data, until there are none left in the RabbitMQ queue.
    while True:
        # Attempt to retrieve a batch of data.
        message_tag, batch = retrieve_batch(channel, comms.TASKS_QUEUE, retries=12, wait_time=5)

        # If a batch was not retrieved.
        if message_tag is None:
            # Close the connection to the RabbitMQ queue and server.
            channel.close()
            connection.close()

            # Print a message and end the program.
            print("exiting: no tasks in queue")
            sys.exit(0)
        
        # Attempt to process the batch of data.
        try:
            # Process the batch of data.
            # Send the processed batch back to the manager.
            processed_batch = process_data(batch)
            comms.send_data([processed_batch], connection, comms.RESULTS_QUEUE)

            # Acknowledge the message as processed to the RabbitMQ queue.
            channel.basic_ack(message_tag)
    
        # In case an exception/error occurs, requeue the batch of data.
        except Exception as e:
            # Print an error message.
            print(f"error: failed to process batch {e}")

            # Don't acknowledge the message and requeue to the RabbitMQ queue.
            channel.basic_nack(message_tag, requeue=True)


def retrieve_batch(channel: pika.channel.Channel, queue_name: str, retries: int, 
                   wait_time: float) -> tuple[int, comms.DataBatch]|tuple[None, None]:
    """
    Retrieves a batch of data (1 message) from a RabbitMQ queue. The function 
    attempts to retrieve a batch of data from the given queue, for a set number 
    of retries in intervals. If a batch of data could not be retrieved, None is 
    returned. The batch of data is expected to be a DataBatch object.

    + Warning: This function does not auto-acknowledge messages.

    Parameters
    ----------
    channel : pika.channel.Channel
        The channel to the RabbitMQ server.

    queue_name : str
        The name of the RabbitMQ queue.

    retries : 
        The number of attempts at retrieving a batch of data.
    
    wait_time : float
        The amount of time to wait between retries (seconds).

    Returns
    -------
    tuple[int, comms.DataBatch] | tuple[None, None] 
        If successful, a tuple containing the delivery-tag of the message and 
        the DataBatch object from the message. Otherwise, a tuple of None is 
        returned.
    """

    # Store the number of attempts.
    attempts = 0

    # Attempt to retrieve a batch of data, for the given number of retries.
    while attempts < retries:
        # Poll the queue for a response.
        response = channel.basic_get(queue_name, auto_ack=False)

        # If a message was returned.
        if response[0] is not None:
            # De-serialise the message.
            # Return both the method-frame (for manual acknowledgement) and the message.
            return (response[0].delivery_tag, pickle.loads(response[2]))
        
        # Otherwise, increase the attempts counter.
        # Wait before the next attempt.
        attempts += 1
        time.sleep(wait_time)

    # If a batch of data was not retrieved, return None.
    return (None, None)


def process_data(batch: comms.DataBatch) -> comms.DataBatch:
    """
    Processes a batch of data for the Higgs to 4-Lepton decay process from the 
    ATLAS Open Data project. A self-contained DataBatch is expected and also 
    returned. 

    Parameters
    ----------
    batch : comms.DataBatch
        A DataBatch object containing the information about the batch of data 
        to process.

    Returns
    -------
    batch : comms.DataBatch
        The passed DataObject with the "processed_data" attribute assigned with 
        the processed data.
    """

    # Create a list to store valid events.
    valid_events = []

    # Print information about the batch of data.
    print(f"Sample      : {batch.sample}\n" +
          f"Subsample   : {batch.subsample}\n" +
          f"Sample Type : {batch.sample_type}")

    # Start a timer.
    start = time.time()

    # If the sample-type is "measured", set the corresponding iteration variables.
    if batch.sample_type == "measured":
        iteration_vars = config.DATA_VARS

    # If the sample-type is "monte-carlo", set the corresponding iteration variables.
    else:
        iteration_vars = config.DATA_VARS + config.WEIGHT_VARS
    
    # Open the data file.
    with uproot.open(batch.path + ":mini") as tree:
        # Filter the valid events in the data.
        for events in tree.iterate(iteration_vars, library="ak", step_size=config.BATCH_SIZE, 
                                   entry_start=batch.start_index, entry_stop=batch.stop_index):
            # Store the number of events before reducing the data.
            num_events_before = len(events)

            # Keep the events with valid lepton type.
            lepton_types = events["lep_type"]
            events = events[valid_lepton_type(lepton_types)]

            # Keep the events with valid lepton charge.
            lepton_charges = events["lep_charge"]
            events = events[valid_lepton_charge(lepton_charges)]

            # Calculate the invariant mass of the remaining events.
            events["mass"] = calc_invariant_mass(events["lep_pt"], events["lep_eta"], 
                                                 events["lep_phi"], events["lep_E"])

            # If the sample-type is "monte-carlo", perform Monte Carlo specific processing.
            if batch.sample_type == "monte-carlo":
                # Calculate the Monte Carlo weights of the events.
                # Calculate the final number of events.
                events["mc_weight"] = calc_mc_weight(events, batch.subsample, config.WEIGHT_VARS)
                num_events_after = sum(events["mc_weight"])

            # Otherwise, proceed as normal.
            else:
                # Calculate the final number of events.
                num_events_after = len(events)

            # Stop the timer.
            runtime = time.time() - start
            print(f"\t Events Before: {num_events_before}" + 
                  f"\t Events After: {num_events_after:.3f}" +
                  f"\t Runtime: {runtime:.3f}")

            # Store the valid events.
            valid_events.append(events)
    
    # Store the processed data.
    batch.processed_data = ak.concatenate(valid_events)

    return batch


def valid_lepton_type(lepton_types: ak.Array) -> ak.Array:
    """
    Determines whether events have the correct lepton type for the Higgs to 
    4-Lepton decay process. The total lepton type of an event should be one of 
    the following to be considered as valid.

    + 44 : electron + electron + electron + electron
    + 48 : electron + electron + muon + muon
    + 52 : muon + muon + muon + muon

    Parameters
    ----------
    lepton_types : awkward.Array
        An awkward array containing the lepton types of the four leptons in 
        each event.
    
    Returns
    -------
    valid : awkward.Array
        An awkward array containing boolean values which are True if an event 
        has a valid total lepton type and False otherwise.
    """

    # Calculate the sum of the lepton types.
    sum_lepton_types = (lepton_types[:, 0] + lepton_types[:, 1] + lepton_types[:, 2] + 
                        lepton_types[:, 3])

    # Determine whether the total lepton type is valid.
    valid = (sum_lepton_types == 44) | (sum_lepton_types == 48) | (sum_lepton_types == 52)

    return valid


def valid_lepton_charge(lepton_charges: ak.Array) -> ak.Array:
    """
    Determines whether events have the correct lepton charge for the Higgs to 
    4-Lepton decay process. The total lepton charge of an event should be 0 to 
    be considered as valid.

    Parameters
    ----------
    lepton_charges : awkward.Array
        An awkward array containing the lepton charges of the four leptons in 
        each event.

    Returns
    -------
    valid : awkward.Array
        An awkward array containing boolean values which are True if an event 
        has a valid total lepton charge and False otherwise.
    """

    # Calculate the sum of the lepton charges.
    sum_lepton_charges = (lepton_charges[:, 0] + lepton_charges[:, 1] + lepton_charges[:, 2] + 
                          lepton_charges[:, 3])

    # Determine whether the total lepton charge is valid.
    valid = (sum_lepton_charges == 0)

    return valid


def calc_invariant_mass(lepton_pt: ak.Array, lepton_eta: ak.Array, lepton_phi: ak.Array, 
                        lepton_E: ak.Array) -> ak.Array:
    """
    Calculates each event's invariant mass of the four lepton state in the 
    Higgs to 4-Lepton decay process.

    Parameters
    ----------
    lepton_pt : awkward.Array
        An awkward array containing the transverse momentums of the four 
        leptons in each event.
    
    lepton_eta : awkward.Array
        An awkward array containing the pseudorapidities of the four leptons in 
        each event.

    lepton_phi : awkward.Array
        An awkward array containing the azimuthal angles of the four leptons in 
        each event.

    lepton_E : awkward.Array
        An awkward array containing the energy of the four leptons in each 
        event.

    Returns
    -------
    invariant_mass : awkward.Array
        An awkward array containing the invariant mass of the four lepton state 
        of each event.
    """

    # Store the four lepton kinematic properties as an awkward array of vectors.
    lepton_data = vector.zip({"pt": lepton_pt, "eta": lepton_eta, "phi": lepton_phi, 
                              "E": lepton_E})

    # Calculate the invariant mass.
    invariant_mass = (lepton_data[:, 0] + lepton_data[:, 1] + lepton_data[:, 2] + 
                      lepton_data[:, 3]).M * config.MEV

    return invariant_mass


def calc_mc_weight(events: ak.Array, subsample: str, weight_variables: list) -> ak.Array:
    """
    Calculates the Monte Carlo weight of events in the Higgs to 4-lepton decay 
    process.

    Parameters
    ----------
    events : ak.Array
        An awkward array containing the data from each event.

    subsample : str
        The subsample (decay process) being studied.

    weight_variables : list
        A list of the variables that contribute to the Monte Carlo weight of 
        the event.

    Returns
    -------
    mc_weight : ak.Array
        An awkward array containing the Monte Carlo weight of each event.
    """

    # Get the information about the subsample being studied.
    subsample_info = infofile.infos[subsample]

    # Calculate the cross section weight.
    numerator = config.LUMINOSITY * 1000 * subsample_info["xsec"]
    denominator = subsample_info["red_eff"] * subsample_info["sumw"]

    cross_section_weight =  numerator / denominator

    # Create a variable to store the Monte Carlo weight.
    mc_weight = cross_section_weight

    # Calculate the Monte Carlo weight.
    # Calculate the product of the weights.
    for weight in weight_variables:
        mc_weight = mc_weight * events[weight]

    return mc_weight


if __name__=="__main__":
    main()
