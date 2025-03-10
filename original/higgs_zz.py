# Import standard libraries.
import time

# Import external libraries.
import awkward as ak
import matplotlib.pyplot as plt
from matplotlib.ticker import AutoMinorLocator
import numpy as np
import uproot
import vector

# Import local modules.
import infofile

# Define energies.
MEV = 0.001
GEV = 1.0

# Define the integrated luminosity for all data.
LUMINOSITY = 10

# Define the root path to the dataset.
PATH = "https://atlas-opendata.web.cern.ch/Legacy13TeV/4lep/"

# Define the samples dictionary for data indexing and identification.
SAMPLES = {
    # Measured data from the ATLAS experiment.
    "data": {
        "list"  : ["data_A", "data_B", "data_C", "data_D"]
    },
    # Monte Carlo simulated background noise from [Z -> e+ e-] or [Z -> mu+ mu-] or [t tbar -> l+ l-] processes.
    r"Background $Z,t\bar{t}$": {
        "list"  : ["Zee", "Zmumu", "ttbar_lep"],
        "color" : "#6b59d3" # Purple
    },
    # Monte Carlo simulated background noise from [Z Z* -> l+ l- l+ l-] process.
    r"Background $ZZ^*$": {
        "list"  : ["llll"],
        "color" : "#ff0000" # Red
    },
    # Monte Carlo simulated signal from [H -> Z Z* -> l+ l- l+ l-] process.
    r"Signal ($m_H$ = 125 GeV)": {
        "list"  : ["ggH125_ZZ4lep", "VBFH125_ZZ4lep", "WH125_ZZ4lep", "ZH125_ZZ4lep"],
        "color" : "#00cdff" # Light Blue
    }
}

# Define the required data variables (keys).
DATA_VARS = ["lep_pt", "lep_eta", "lep_phi", "lep_E", "lep_charge", "lep_type"]

# Define the required Monte Carlo weight variables (keys).
WEIGHT_VARS = ["mcWeight", "scaleFactor_PILEUP", "scaleFactor_ELE", "scaleFactor_MUON", "scaleFactor_LepTRIGGER"]

# Create a variable to control the number of events processed.
FRACTION = 1.0


def main():
    """
    Processes the data for the Higgs to 4-Lepton decay process from the ATLAS 
    Open Data project.
    """

    # Define a dictionary to store the final processed data.
    processed_data = {}

    # Loop over all the samples.
    for sample in SAMPLES:
        # Print the sample being processed.
        print(f"Processing: {sample}")

        # Define a list to hold the sample's processed data.
        sample_processed_data = []

        # Loop over subsample in the sample.
        for subsample in SAMPLES[sample]["list"]:
            # If the sample is measured data.
            if sample == "data":
                prefix = "Data/"
            
            # If the sample is Monte Carlo data.
            else:
                prefix = "MC/mc_" + str(infofile.infos[subsample]["DSID"]) + "."

            # Create the path to the subsample.
            path_subsample = PATH + prefix + subsample + ".4lep.root"

            # Start the clock.
            start_time = time.time()
            print("\t" + subsample + ":")

            # Open the subsample's file.
            tree = uproot.open(path_subsample + ":mini")

            # Create a list to store the valid events.
            valid_events = []

            # Filter the valid events in the data.
            for data in tree.iterate(DATA_VARS + WEIGHT_VARS, library="ak", step_size=1000000,
                                    entry_stop=(tree.num_entries * FRACTION)):
                
                # Store the number of events before reduction in the data.
                num_events_before = len(data)

                # Keep the events with valid lepton type.
                lepton_types = data["lep_type"]
                data = data[valid_lepton_type(lepton_types)]

                # Keep the events with valid lepton charge.
                lepton_charges = data["lep_charge"]
                data = data[valid_lepton_charge(lepton_charges)]

                # Calculate the invariant mass of the remaining events.
                data["mass"] = calc_invariant_mass(data["lep_pt"], data["lep_eta"], data["lep_phi"], data["lep_E"])

                # If the data is from Monte Carlo simulation, perform Monte Carlo specific processing.
                if "data" not in subsample:
                    # Calculate the Monte Carlo weights of the events.
                    data["mc_weight"] = calc_mc_weight(data, subsample, WEIGHT_VARS)

                    # Calculate the final number of events.
                    num_events_after = sum(data["mc_weight"])

                # Otherwise, proceed as normal.
                else:
                    # Calculate the final number of events.
                    num_events_after = len(data)

                # Stop the timer.
                runtime = time.time() - start_time
                print(f"\t Num Events Before: {num_events_before}" + 
                      f"\t Num Events After: {num_events_after:.3f}" +
                      f"\t Runtime: {runtime:.3f}")

                # Save the current batch of data to the valid events list.
                valid_events.append(data)

            # Save the subsample's processed data.
            sample_processed_data.append(ak.concatenate(valid_events))
        
        # Save the sample's processed data.
        processed_data[sample] = ak.concatenate(sample_processed_data)

    # Plot the processed data (saved as a png).
    plot_data(processed_data)


def valid_lepton_type(lepton_types: ak.Array) -> ak.Array:
    """
    Determines whether an event has the correct lepton type for the Higgs decay 
    process. The total lepton type of an event should be one of the following 
    to be considered as valid.

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
    sum_lepton_types = lepton_types[:, 0] + lepton_types[:, 1] + lepton_types[:, 2] + lepton_types[:, 3]

    # Determine whether the total lepton type is valid.
    valid = (sum_lepton_types == 44) | (sum_lepton_types == 48) | (sum_lepton_types == 52)

    return valid


def valid_lepton_charge(lepton_charges: ak.Array) -> ak.Array:
    """
    Determines whether an event has the correct lepton charge for the Higgs 
    decay process. The total lepton charge of an event should be 0 to be 
    considered as valid.

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
    sum_lepton_charges = lepton_charges[:, 0] + lepton_charges[:, 1] + lepton_charges[:, 2] + lepton_charges[:, 3]

    # Determine whether the total lepton charge is valid.
    valid = (sum_lepton_charges == 0)

    return valid


def calc_invariant_mass(lepton_pt: ak.Array, lepton_eta: ak.Array, 
                        lepton_phi: ak.Array, lepton_E: ak.Array) -> ak.Array:
    """
    Calculates the invariant mass of the four lepton state of an event in the 
    Higgs decay process.

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
    lepton_data = vector.zip({"pt": lepton_pt, "eta": lepton_eta, "phi": lepton_phi, "E": lepton_E})

    # Calculate the invariant mass.
    invariant_mass = (lepton_data[:, 0] + lepton_data[:, 1] + lepton_data[:, 2] + lepton_data[:, 3]).M * MEV

    return invariant_mass

def calc_mc_weight(events: ak.Array, sample: str, weight_variables: list) -> ak.Array:
    """
    Calculates the Monte Carlo weight of an event.

    Parameters
    ----------
    events : ak.Array
        An awkward array containing the data from each event.

    sample : str
        The sample (decay process) being studied.

    weight_variables : list
        A list of the variables that contribute to the Monte Carlo weight of 
        the event.

    Returns
    -------
    mc_weight : ak.Array
        An awkward array containing the Monte Carlo weight of each event.
    """

    # Get the information about the sample being studied.
    sample_info = infofile.infos[sample]

    # Calculate the cross section weight.
    cross_section_weight = (LUMINOSITY * 1000 * sample_info["xsec"]) / (sample_info["red_eff"] * sample_info["sumw"])

    # Create a variable to store the Monte Carlo weight.
    mc_weight = cross_section_weight

    # Calculate the Monte Carlo weight.
    # Calculate the product of the weights.
    for weight in weight_variables:
        mc_weight = mc_weight * events[weight]

    return mc_weight


def plot_data(data: dict) -> None:
    """
    Generates a histogram plot using the processed data. The processed data 
    should be for the Higgs to 4-Lepton decay process from the ATLAS Open Data 
    project.

    Parameters
    ----------
    data : dict
        A dictionary containing awkward arrays of the processed data for the 
        Higgs to 4-Lepton decay process from the ATLAS Open Data project.
    """

    # Define the x-axis range of the plot.
    x_min = 80 * GEV
    x_max = 250 * GEV

    # Setup the histogram bins.
    bin_width = 5 * GEV
    bin_edges = np.arange(start=x_min, stop=(x_max+bin_width), step=bin_width)
    bin_centres = np.arange(start=(x_min+(bin_width/2)), stop=(x_max+(bin_width/2)), step=bin_width)

    # Setup the measured data for the histogram.
    measured_data_binned, _ = np.histogram(ak.to_numpy(data["data"]["mass"]), bins=bin_edges)
    measured_data_errors = np.sqrt(measured_data_binned)

    # Setup the Monte Carlo simulated signal data for the histogram.
    mc_signal_data = ak.to_numpy(data[r"Signal ($m_H$ = 125 GeV)"]["mass"])
    mc_signal_weights = ak.to_numpy(data[r"Signal ($m_H$ = 125 GeV)"].mc_weight)
    mc_signal_color = SAMPLES[r"Signal ($m_H$ = 125 GeV)"]["color"]

    # Setup the Monte Carlo simulated background data (multiple) for the histogram.
    mc_backgrounds_data = []
    mc_backgrounds_weights = []
    mc_backgrounds_colors = []
    mc_backgrounds_labels = []

    # Loop over all the samples.
    for sample in SAMPLES:
        # Exclude the non Monte Carlo simulated data.
        if sample not in ["data", r"Signal ($m_H$ = 125 GeV)"]:
            # Setup the Monte Carlo simulated background data for the histogram.
            mc_backgrounds_data.append(ak.to_numpy(data[sample]["mass"]))
            mc_backgrounds_weights.append(ak.to_numpy(data[sample].mc_weight))
            mc_backgrounds_colors.append(SAMPLES[sample]["color"])
            mc_backgrounds_labels.append(sample)

    # Calculate the errors.
    mc_backgrounds_errors = np.sqrt(np.histogram(np.hstack(mc_backgrounds_data), bins=bin_edges, 
                                                 weights=(np.hstack(mc_backgrounds_weights)**2))[0])
    
    # Create the main plot.
    fig, ax = plt.subplots()

    # Plot the measured data.
    ax.errorbar(x=bin_centres, y=measured_data_binned, yerr=measured_data_errors, fmt="ko", label="Data")

    # Plot the Monte Carlo simulated background data.
    # Save the heights of the bars.
    mc_backgrounds_heights = ax.hist(mc_backgrounds_data, bins=bin_edges, weights=mc_backgrounds_weights,
                                     stacked=True, color=mc_backgrounds_colors, label=mc_backgrounds_labels)
    
    # Get the tallest heights of the bars.
    mc_backgrounds_tallest = mc_backgrounds_heights[0][-1]

    # Plot the statistical uncertainty in the Monte Carlo simulated background data.
    ax.bar(bin_centres, (2*mc_backgrounds_errors), bottom=(mc_backgrounds_tallest-mc_backgrounds_errors),
           color="none", alpha=0.5, hatch="////", width=bin_width, label="Stat. Unc.")

    # Plot the Monte Carlo simulated signal data.
    ax.hist(mc_signal_data, bins=bin_edges, bottom=mc_backgrounds_tallest, weights=mc_signal_weights, 
            color=mc_signal_color, label=r"Signal ($m_H$ = 125 GeV)")
    
    # Set the x-axis and y-axis limits.
    ax.set_xlim(left=x_min, right=x_max)
    ax.set_ylim(bottom=0, top=(np.amax(measured_data_binned)*1.6))

    # Set the x-axis and y-axis minor ticks.
    ax.xaxis.set_minor_locator(AutoMinorLocator())
    ax.yaxis.set_minor_locator(AutoMinorLocator())

    # Set the tick parameters.
    ax.tick_params(which="both", direction="in", top=True, right=True)

    # Set the x-axis label.
    ax.set_xlabel(r"4-lepton invariant mass $\mathrm{m_{4l}}$ [GeV]", fontsize=13, x=1, horizontalalignment="right")
    
    # Set the y-axis label.
    ax.set_ylabel(f"Events / {bin_width} GeV", y=1, horizontalalignment="right") 

    # Add "ATLAS Open Data" text.
    plt.text(0.05, 0.93, "ATLAS Open Data", transform=ax.transAxes, fontsize=13)

    # Add "for education" text.
    plt.text(0.05, 0.88, "for education", transform=ax.transAxes, fontsize=13, style="italic")

    # Add text to show the energy and luminosity.
    energy_luminosity_text = r"$\sqrt{s}$=13 TeV,$\int$L dt = " + str(LUMINOSITY * FRACTION) + r" fb$^{-1}$"
    plt.text(0.05, 0.82, energy_luminosity_text, transform=ax.transAxes)

    # Add text to show the studied decay process (Higgs to 4-Lepton).
    plt.text(0.05, 0.76, r"$H \rightarrow ZZ^* \rightarrow 4\ell$", transform=ax.transAxes)
 
    # Draw the legend.
    ax.legend(frameon=False)

    # Save the figure.
    plt.savefig("higgs_zz.png")


if __name__ == "__main__":
    main()