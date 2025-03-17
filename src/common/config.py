# Define the root path (URL) to the ATLAS dataset.
PATH = "https://atlas-opendata.web.cern.ch/Legacy13TeV/4lep/"

# Define the fraction of the full ATLAS dataset to process.
FRACTION = 1.0

# Define the batch size of each data batch.
BATCH_SIZE = 100000

# Define the samples to process from the ATLAS dataset.
# Define the colours for plotting.
SAMPLES = {
    # Measured data from the ATLAS experiment.
    "data": {
        "list"  : ["data_A", "data_B", "data_C", "data_D"]
    },

    # Monte Carlo simulated background noise from [Z -> e+ e-], [Z -> mu+ mu-], [t tbar -> l+ l-] processes.
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

# Define the energies.
MEV = 0.001
GEV = 1.0

# Define the integrated luminosity (fb^{-1}).
LUMINOSITY = 10

# Define the variables used for processing data (keys).
DATA_VARS = ["lep_pt", 
             "lep_eta", 
             "lep_phi", 
             "lep_E", 
             "lep_charge", 
             "lep_type"]

# Define the extra variables used for processing Monte Carlo data (keys).
WEIGHT_VARS = ["mcWeight", 
               "scaleFactor_PILEUP", 
               "scaleFactor_ELE", 
               "scaleFactor_MUON", 
               "scaleFactor_LepTRIGGER"]