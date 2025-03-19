# Import standard libraries.
import time
import sys
import uuid

# Import external libraries.
import awkward as ak
import matplotlib.pyplot as plt
from matplotlib.ticker import AutoMinorLocator
import numpy as np
import pickle
import pika
import uproot

# Import local modules.
import comms
import config
import infofile


def main():
    """
    Represents a manager node that batches data and sends it workers for 
    processing. The processed batches are then re-collected and a figure is 
    generated. The data being processed is the data for the Higgs to 4-Lepton 
    decay process from the ATLAS Open Data project. The manager node stops 
    re-collecting data after a given termination period.
    """

    # Open a connection to the RabbitMQ server.
    connection = comms.open_connection(comms.RABBITMQ_SERVER, retries=6, wait_time=5)

    # If a connection cannot be established, print an error and terminate.
    if connection is None:
        print("error: RabbitMQ connection failed")
        sys.exit(1)

    # Batch the data that needs to be processed.
    batches = data_batcher(config.SAMPLES, config.PATH, config.FRACTION, config.BATCH_SIZE)

    # Print the number of batches.
    print(f"status: number of batches - {len(batches)}")

    # Send the batches of data to the workers.
    comms.send_data(batches, connection, comms.TASKS_QUEUE)

    # Retrieve the processed batches of data from the workers.
    processed_batches = retrieve_batches(connection, comms.RESULTS_QUEUE, len(batches), 
                                         wait_time=1, terminate_time=240)
    
    # Close the connection to the RabbitMQ server.
    connection.close()

    # If no processed batches of data could be retrieved, print an error and terminate.
    if len(processed_batches) == 0:
        print("error: failed to retrieve processed data")
        sys.exit(1)
    
    # Check for missing batches of data.
    missing_data_batches = missing_batches(batches, processed_batches)

    # If there are missing batches of data.
    if missing_data_batches is not None:
        # If the more than half the batches are missing, print an error and terminate.
        if len(missing_data_batches) > len(batches) // 2:
            print("error: missing more than 50% of the expected data")
            sys.exit(1)

        # Otherwise, print the missing batches.
        else:
            # Print a warning.
            print("warning: missing the following batches of data")

            # Print the information of each missing batch.
            for batch in missing_batches:
                print(batch)

            # Print another warning.
            print("warning: attempting to proceed")

    # Group the processed batches of data according to their sample.
    samples_data = group_batches(processed_batches, config.SAMPLES)

    # Ensure that each sample has a minimum number of events.
    for sample in config.SAMPLES:
        # If the sample has no events, print an error and terminate.
        if len(samples_data[sample]) == 0:
            print(f"error: no data for sample - {sample}")
            sys.exit(1)

        # If the sample has less than 50 events, print a warning.
        elif len(samples_data[sample]) < 50:
            print(f"warning: less than 50 events for sample - {sample}")
    
    # Generate the final plot.
    plot_data(samples_data, "output/higgs_zz.png")

    # Print a success message.
    print(f"success: figure created")


def data_batcher(samples: dict, path: str, fraction: float, 
                 batch_size: int) -> list[comms.DataBatch]:
    """
    Creates batches of data using the DataBatch object. The data is expected to 
    be data for the Higgs to 4-Lepton decay process from the ATLAS Open Data 
    project.

    Parameters
    ----------
    samples : dict
        A dictionary containing information about the samples and subsamples 
        being processed.
    
    path : str
        The root path (URL) to the ATLAS dataset being processed.

    fraction : float
        The fraction of the full ATLAS dataset to process.
    
    batch_size : int
        The size of each batch (number of events).

    Returns
    -------
    batches : list[comms.DataBatch]
        A list of DataBatch objects which contain information about each batch 
        of data.
    """

    # Create a list to store each batch of data.
    batches = []

    # Loop through each sample.
    for sample in samples:
        # Loop through each subsample.
        for subsample in samples[sample]["list"]:
            # If the sample is "data", it corresponds to measured data. 
            if sample == "data":
                # Set the sample-type and path prefix.
                sample_type = "measured"
                prefix = "Data/"

            # Otherwise, it corresponds to Monte Carlo data.
            else:
                # Set the sample-type and path prefix.
                sample_type = "monte-carlo"
                prefix = "MC/mc_" + str(infofile.infos[subsample]["DSID"]) + "."

            # Construct the path to the subsample data file.
            path_subsample = path + prefix + subsample + ".4lep.root"

            # Open the meta-data of the subsample data file.
            with uproot.open(path_subsample + ":mini") as tree:
                # Get the number of events in the data.
                data_num_events = tree.num_entries

            # Calculate the number of events to process.
            # Ensure the maximum number of events are not exceeded.
            num_events = min(data_num_events, round(data_num_events * fraction))

            # Batch the subsample data file into batches with the given batch size.
            # Generate a DataBatch object for each batch of the subsample data file.
            for start in range(0, num_events, batch_size):
                # Calculate the stop-index.
                # Calculate the batch fraction (fraction of total events being processed).
                stop = min(start + batch_size, num_events)
                batch_fraction = (stop - start) / num_events

                # Generate a DataBatch object for the batch of the subsample data file.
                batches.append(comms.DataBatch(str(uuid.uuid4()), sample, subsample, sample_type, 
                                               path_subsample, batch_fraction, start, stop))

    return batches


def group_batches(batches: list[comms.DataBatch], samples: dict) -> dict[str, ak.Array]:
    """
    Groups batches of processed data based on the sample each batch belongs to.

    Parameters
    ----------
    batches: list[communication.DataBatch]
        A list of DataBatch objects which have their "processed_data" attribute 
        filled with an awkward array of processed data.
    
    samples : dict
        A dictionary containing information about the samples and subsamples 
        being processed.

    Returns
    -------
    samples_data : dict[awkward.Array]
        A dictionary containing the processed data for each sample.
    """

    # Create a dictionary to store the data for each sample.
    samples_data = {}

    # Loop through each sample.
    for sample in samples:
        # Create a list to store the batches of data for the sample.
        samples_data[sample] = []

        # Loop through each batch of data.
        for batch in batches:
            # If the the batch corresponds to the sample, store its processed data.
            if batch.sample == sample:
                samples_data[sample].append(batch.processed_data)

        # Combine the batches of data for the sample into an awkward array.
        samples_data[sample] = ak.concatenate(samples_data[sample])
    
    return samples_data


def missing_batches(expected_batches: list[comms.DataBatch], 
                    retrieved_batches: list[comms.DataBatch]) -> list[comms.DataBatch]|None:
    """
    Checks for missing batches of processed data through cross checking batch 
    ID's between sent and retrieved DataBatch objects. The function returns the 
    missing DataBatch objects. If there are no missing batches, None is 
    returned.

    Parameters
    ----------
    expected_batches : list[comms.DataBatch]
        A list of the expected DataBatch objects.

    retrieved_batches : list[comms.DataBatch]
        A list of the retrieved DataBatch objects.

    Returns
    -------
    list[comms.DataBatch] | None
        If there are missing batches of data, a list of the missing DataBatch 
        objects. Otherwise, None is returned. 
    """

    # Create a dict which maps expected batch IDs to the corresponding DataBatch object.
    expected_batches_map = {batch.batch_id: batch for batch in expected_batches}

    # Create a set of retrieved batch IDs.
    retrieved_batch_ids = {batch.batch_id for batch in retrieved_batches}

    # Get the missing batch IDs.
    missing_batch_ids = set(expected_batches_map.keys()) - retrieved_batch_ids

    # If there are no missing batches, return None.
    if len(missing_batch_ids) == 0:
        return None

    # Create a list of the missing batches.
    missing_batches = [expected_batches_map[batch_id] for batch_id in missing_batch_ids]

    return missing_batches


def retrieve_batches(connection: pika.BlockingConnection, queue_name: str, num_batches: int, 
                     wait_time: float, terminate_time: float) -> list[comms.DataBatch]:
    """
    Retrieves batches of data from a RabbitMQ queue. The function polls the 
    RabbitMQ queue at given intervals, until either the number of expected 
    batches are retrieved or the termination time is reached.

    Parameters
    ----------
    connection : pika.BlockingConnection
        The connection to the RabbitMQ server.

    queue_name : str
        The name of the RabbitMQ queue.

    num_batches : int
        The number of expected batches.

    wait_time : float
        The amount of time to wait between polls (seconds).

    termination_time : float
        The amount of time to poll before terminating.

    Returns
    -------
    batches : list[DataBatch]
        A list of the DataBatch objects retrieved from the RabbitMQ queue.
    """

    # Start a timer.
    start = time.time()

    # Create a list to store the batches.
    batches = []

    # Create a channel and declare the queue.
    channel = connection.channel()
    channel.queue_declare(queue_name)

    # Poll the RabbitMQ queue until given number of batches are retrieved.
    # This loop also terminates if the termination time is reached.
    while len(batches) != num_batches:
        # Poll the queue for a response.
        response = channel.basic_get(queue_name, auto_ack=True)

        # If a response was returned.
        if response[0] is not None:
            # De-serialise the message and store it.
            batches.append(pickle.loads(response[2]))

        # If the termination time has been reached.
        if time.time() - start > terminate_time:
            # Close the channel and return the retrieved batches.
            channel.close()
            return batches
        
        # Wait before the next poll.
        time.sleep(wait_time)

    # Close the channel.
    channel.close()

    return batches


def plot_data(data: dict[str, ak.Array], filename: str) -> None:
    """
    Generates a histogram plot using processed data for the Higgs to 4-Lepton 
    decay process from the ATLAS Open Data project.

    Parameters
    ----------
    data : dict[str, ak.Array]
        A dictionary containing awkward arrays of the processed data for each 
        sample in the Higgs to 4-Lepton decay process.

    filename : str
        The filename to save the figure to.
    """

    # Define the x-axis range of the plot.
    x_min = 80 * config.GEV
    x_max = 250 * config.GEV

    # Setup the histogram bins.
    bin_width = 5 * config.GEV
    bin_edges = np.arange(start=x_min, stop=(x_max+bin_width), step=bin_width)
    bin_centres = np.arange(start=(x_min+(bin_width/2)), stop=(x_max+(bin_width/2)), step=bin_width)

    # Setup the measured data for the histogram.
    measured_data_binned, _ = np.histogram(ak.to_numpy(data["data"]["mass"]), bins=bin_edges)
    measured_data_errors = np.sqrt(measured_data_binned)

    # Setup the Monte Carlo simulated signal data for the histogram.
    mc_signal_data = ak.to_numpy(data[r"Signal ($m_H$ = 125 GeV)"]["mass"])
    mc_signal_weights = ak.to_numpy(data[r"Signal ($m_H$ = 125 GeV)"].mc_weight)
    mc_signal_color = config.SAMPLES[r"Signal ($m_H$ = 125 GeV)"]["color"]

    # Setup the Monte Carlo simulated background data (multiple) for the histogram.
    mc_backgrounds_data = []
    mc_backgrounds_weights = []
    mc_backgrounds_colors = []
    mc_backgrounds_labels = []

    # Loop over all the samples.
    for sample in config.SAMPLES:
        # Exclude the non Monte Carlo simulated data.
        if sample not in ["data", r"Signal ($m_H$ = 125 GeV)"]:
            # Setup the Monte Carlo simulated background data for the histogram.
            mc_backgrounds_data.append(ak.to_numpy(data[sample]["mass"]))
            mc_backgrounds_weights.append(ak.to_numpy(data[sample].mc_weight))
            mc_backgrounds_colors.append(config.SAMPLES[sample]["color"])
            mc_backgrounds_labels.append(sample)

    # Calculate the errors.
    mc_backgrounds_errors = np.sqrt(np.histogram(np.hstack(mc_backgrounds_data), bins=bin_edges, 
                                                 weights=(np.hstack(mc_backgrounds_weights)**2))[0])
    
    # Create the main plot.
    fig, ax = plt.subplots()

    # Plot the measured data.
    ax.errorbar(x=bin_centres, y=measured_data_binned, yerr=measured_data_errors, fmt="ko", 
                label="Data")

    # Plot the Monte Carlo simulated background data.
    # Save the heights of the bars.
    mc_backgrounds_heights = ax.hist(mc_backgrounds_data, bins=bin_edges, 
                                     weights=mc_backgrounds_weights, stacked=True, 
                                     color=mc_backgrounds_colors, label=mc_backgrounds_labels)
    
    # Get the tallest heights of the bars.
    mc_backgrounds_tallest = mc_backgrounds_heights[0][-1]

    # Plot the statistical uncertainty in the Monte Carlo simulated background data.
    ax.bar(bin_centres, (2*mc_backgrounds_errors), 
           bottom=(mc_backgrounds_tallest-mc_backgrounds_errors),
           color="none", alpha=0.5, hatch="////", width=bin_width, label="Stat. Unc.")

    # Plot the Monte Carlo simulated signal data.
    ax.hist(mc_signal_data, bins=bin_edges, bottom=mc_backgrounds_tallest, 
            weights=mc_signal_weights, color=mc_signal_color, label=r"Signal ($m_H$ = 125 GeV)")
    
    # Set the x-axis and y-axis limits.
    ax.set_xlim(left=x_min, right=x_max)
    ax.set_ylim(bottom=0, top=(np.amax(measured_data_binned)*1.6))

    # Set the x-axis and y-axis minor ticks.
    ax.xaxis.set_minor_locator(AutoMinorLocator())
    ax.yaxis.set_minor_locator(AutoMinorLocator())

    # Set the tick parameters.
    ax.tick_params(which="both", direction="in", top=True, right=True)

    # Set the x-axis label.
    ax.set_xlabel(r"4-lepton invariant mass $\mathrm{m_{4l}}$ [GeV]", fontsize=13, x=1, 
                  horizontalalignment="right")
    
    # Set the y-axis label.
    ax.set_ylabel(f"Events / {bin_width} GeV", y=1, horizontalalignment="right") 

    # Add "ATLAS Open Data" text.
    plt.text(0.05, 0.93, "ATLAS Open Data", transform=ax.transAxes, fontsize=13)

    # Add "for education" text.
    plt.text(0.05, 0.88, "for education", transform=ax.transAxes, fontsize=13, style="italic")

    # Add text to show the energy and luminosity.
    energy_luminosity_text = (r"$\sqrt{s}$=13 TeV,$\int$L dt = " + 
                              str(config.LUMINOSITY * config.FRACTION) + 
                              r" fb$^{-1}$")
    plt.text(0.05, 0.82, energy_luminosity_text, transform=ax.transAxes)

    # Add text to show the studied decay process (Higgs to 4-Lepton).
    plt.text(0.05, 0.76, r"$H \rightarrow ZZ^* \rightarrow 4\ell$", transform=ax.transAxes)
 
    # Draw the legend.
    ax.legend(frameon=False)

    # Save the figure.
    plt.savefig(filename)


if __name__=="__main__":
    main()