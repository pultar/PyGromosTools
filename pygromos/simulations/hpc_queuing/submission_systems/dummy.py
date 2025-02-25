import warnings
from typing import Union, List

from pygromos.simulations.hpc_queuing.submission_systems._submission_system import _SubmissionSystem


class DUMMY(_SubmissionSystem):
    """DUMMY
        This SubmissionSystem is for testing submission systems. It basically prints everything out.
    """

    def __init__(self, verbose: bool = False, nomp: int = 1, nmpi: int = 1, job_duration: str = "24:00",
                 submission: bool = True, enviroment=None):
        super().__init__(verbose=verbose, nmpi=nmpi, nomp=nomp, job_duration=job_duration, submission=submission, enviroment=enviroment)

    def submit_to_queue(self, command: str, **kwargs) -> Union[int, None]:
        """submit_to_queue
            This function submits a str command to the submission system.

        Parameters
        ----------
        command : str
            command to be submitted
        kwargs

        Returns
        -------
        int, None
            if a job was submitted the jobID is returned else None.

        """
        if (self.submission):
            print("\n", command, "\n")
            return 0
        else:
            print('did not submit')
            return None

    def submit_jobAarray_to_queue(self, command: str, start_Job: int, end_job: int,
                                  **kwargs) -> Union[int, None]:
        """submit_jobAarray_to_queue
            this function is submitting
        Parameters
        ----------
        command : str
            the command to be submitted
        start_Job : int
            ind of the starting job
        end_job : int
            end job index.
        kwargs

        Returns
        -------
        int, None
            if a job was submitted the jobID is returned else None.

        """
        if (self.submission):
            print()
            for jobID in range(start_Job, end_job + 1):
                print("Job " + str(jobID) + ":", command, "\n")
            print()
            return 0
        else:
            print('did not submit')
            return None

    def get_jobs_from_queue(self, job_text: str, **kwargs) -> List[int]:
        """search_queue_for_jobname

            this jobs searches the job queue for a certain job id.

        Parameters
        ----------
        job_text :  str
        regex:  bool, optional
            if the string is a Regular Expression
        Returns
        -------
        List[int]
            output contains all ids of fitting jobs to the querry
        """
        if (self.verbose): print("Retrieving jobs from list with: ", job_text)
        warnings.warn("Queue search was called, but no queue present!")
        return []

    def search_queue_for_jobname(self, job_name: str, **kwargs) -> List[str]:
        """search_queue_for_jobname

            this jobs searches the job queue for a certain job id.

        Parameters
        ----------
        job_name :  str
        regex:  bool, optional
            if the string is a Regular Expression
        Returns
        -------
        List[str]
            the output of the queue containing the jobname
        """
        if (self.verbose): print("Searching job Name: ", job_name)
        warnings.warn("Queue search was called, but no queue present!")
        return []