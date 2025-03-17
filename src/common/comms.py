# Import standard libraries.
import time

# Import external libraries.
import pickle
import pika

# Define the name of the RabbitMQ server.
RABBITMQ_SERVER = "rabbitmq"

# Define the name of the tasks and results queue.
TASKS_QUEUE = "tasks"
RESULTS_QUEUE = "results"


class DataBatch:
    """
    A class that represents a batch of data. It aims to be self contained, i.e. 
    all the information about the batch of data is contained within the class.

    Attributes
    ----------
    batch_id : str
        The unique identifier of the batch.

    sample : str
        The sample that the batch belongs to.
    
    subsample : str
        The subsample that the batch belongs to.
    
    sample_type : str, enum = ["measured", "monte-carlo"]
        The sample type of the sample that the batch belongs to. This should be 
        either "measured" (real data) or "monte-carlo" (simulated data).
    
    path : str
        The path (URL) to the file containing the data for the batch.
    
    fraction : float
        The fraction of the subsample data that the batch contains.
    
    start_index : int
        The starting index in the data array of the batch.
    
    stop_index : int
        The stopping index in the data array of the batch.
    
    processed_data : ak.Array
        The processed data for the batch.
    """

    def __init__(self, batch_id: str, sample: str, subsample: str, sample_type: str, path: str, 
                 fraction: float, start_index: int, stop_index: int) -> None:
        """
        Initialises an instance of the DataBatch class. View the class 
        docstring for information about its attributes.

        Parameters
        ----------
        batch_id : str
            The unique identifier of the batch.
        
        sample : str
            The sample that the batch belongs to.
        
        subsample : str
            The subsample that the batch belongs to.
        
        sample_type : str, enum = ["measured", "monte-carlo"]
            The sample type of the sample that the batch belongs to. This 
            should be either "measured" (real data) or "monte-carlo" (simulated 
            data).
        
        path : str
            The path (URL) to the file containing the data for the batch.
        
        fraction : float
            The fraction of the subsample data that the batch contains.
        
        start_index : int
            The starting index in the data array of the batch.
        
        stop_index : int
            The stopping index in the data array of the batch.
        """

        # Set the batch's unique identifier.
        self.batch_id = batch_id

        # Set the sample, subsample and sample-type of the batch.
        self.sample = sample
        self.subsample = subsample
        self.sample_type = sample_type

        # Set the path to the subsample data file.
        self.path = path

        # Set the fraction of subsample data the batch contains.
        self.fraction = fraction

        # Set the starting and stopping index (data array) of the batch.
        self.start_index = start_index
        self.stop_index = stop_index

        # Initialise the processed data attribute to None.
        self.processed_data = None

    def __str__(self) -> str:
        """
        Returns a string that contains information about the instance of the 
        DataBatch object.
        """
        
        return (f"Batch ID          : {self.batch_id}       \n" +
                f"Sample            : {self.sample}         \n" + 
                f"Subsample         : {self.subsample}      \n" +
                f"Sample Type       : {self.sample_type}    \n" +
                f"Path              : {self.path}           \n" +
                f"Fraction          : {self.fraction}       \n" +
                f"Start Index       : {self.start_index}    \n" +
                f"Stop Index        : {self.stop_index}     \n" +
                f"Processed Data    : {self.processed_data}")


def open_connection(hostname: str, retries: int, wait_time: float) -> pika.BlockingConnection|None:
    """
    Opens and returns a connection to a RabbitMQ server. The function attempts 
    to open a connection to the given hostname, for a set number of retries in 
    intervals. If a connection cannot be opened, None is returned.

    Parameters
    ----------
    hostname : str
        The hostname of the RabbitMQ server.

    retries : int
        The number of attempts at opening a connection.

    wait_time : float
        The amount of time to wait between retries (seconds).

    Returns
    -------
    connection : pika.BlockingConnection | None
        If successful, a connection to the RabbitMQ server. Otherwise, None is 
        returned.
    """

    # Store the number of connection attempts.
    attempts = 0

    # Attempt to open a connection, for the given number of retries.
    while attempts < retries:
        # Attempt to open a connection to the RabbitMQ server.
        try:
            # If a connection can be established, return it.
            connection = pika.BlockingConnection(pika.ConnectionParameters(hostname))
            return connection

        # If a connection cannot be established.
        except pika.exceptions.AMQPConnectionError:
            # Update the number of attempts.
            attempts += 1

            # If the number of attempts is less than the number of retries.
            # Wait before the next attempt.
            if attempts < retries:
                time.sleep(wait_time)

            # Otherwise, return None.
            else:
                return None

    # Just in case the loop is exited (unexpected), return None.
    return None            


def send_data(batches: list[DataBatch], connection: pika.BlockingConnection, 
              queue_name: str) -> None:
    """
    Sends batches of data to a RabbitMQ queue as individual messages. A list of 
    DataBatch objects are expected.

    Parameters
    ----------
    batches : list[DataBatch]
        A list of DataBatch objects which represent batches of data.

    connection : pika.BlockingConnection
        The connection to the RabbitMQ server.

    queue_name : str
        The name of the RabbitMQ queue.
    """
    
    # Open a channel and declare the queue.
    channel = connection.channel()
    channel.queue_declare(queue_name)
    
    # Send each batch of data.
    for batch in batches:
        # Serialise the batch using pickle and send it to the queue.
        pickled_batch = pickle.dumps(batch)
        channel.basic_publish(exchange="", routing_key=queue_name, body=pickled_batch)

    # Close the channel.
    channel.close()
