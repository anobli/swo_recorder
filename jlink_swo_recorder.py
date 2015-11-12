#! /usr/bin/python

#
# Copyright (c) 2015 Google Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 1. Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
# 3. Neither the name of the copyright holder nor the names of its
# contributors may be used to endorse or promote products derived from this
# software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

import os
import sys
import select
import getopt
import signal
import telnetlib
import subprocess
import socket
import time

from daemon import runner

# Stop gdb and stop the recorder
def signal_handler(signum, frame):
	recorder.record = False
	recorder.gdb.send_signal(signal.SIGINT)

# Helper to run commands in another process
def async_call(cmd, debug):
	# FIXME Use the pipe to print logs
	if debug == "1":
		p = subprocess.Popen(cmd)
	else:
		p = subprocess.Popen(cmd, stdin = subprocess.PIPE,
							stdout = subprocess.PIPE, stderr = subprocess.PIPE)
	return p

class SWORecorder:
	def __init__(self):
		# daemon consoles: required by the DaemonRunner
		self.stdin_path = '/dev/null'
		self.stdout_path = '/dev/tty'
		self.stderr_path = '/dev/tty'

		# daemon path and files
		self.pwd = os.getenv("PWD")
		self.prefix = os.path.abspath(os.path.dirname(__file__))
		self.script_path = self.prefix + '/scripts'
		self.pidfile_path =  self.pwd + '/testdaemon.pid'

		self.pidfile_timeout = 5
		self.record = True

		# JLINK options
		self.jlink_path = os.getenv("JLINK_PATH", "opt/jlink")
		# host and port of SWO console
		self.jlink_port = 2332
		self.jlink_host = "127.0.0.1"

		# Set to 1 to print more logs
		self.debug = os.getenv("RECORDER_DEBUG", "0")

		# Set to 1 to reset the target before to record trace
		self.reset = os.getenv("FW_RESET", "1")

		# Traces output file
		self.output = os.getenv("TRACE_OUTPUT", self.pwd + '/traces')

	# Wrapper to run gdb commands
	def run_gdb(self, script, wait=0):
		if self.debug == "1":
			batch = "--batch"
		else:
			batch = "--batch-silent"
		cmd = [
			"arm-none-eabi-gdb", batch,
			"-x", self.script_path + "/trace_function.gdb",
			"-x", self.script_path + "/jlink_trace_function.gdb",
			"-x", self.script_path + "/" + script
		]
		if wait == 0:
			self.gdb = async_call(cmd, self.debug)
		else:
			subprocess.call(cmd)

	def run(self):
		# Handle some signals to stop the recorder
		signal.signal(signal.SIGTERM, signal_handler)
		signal.signal(signal.SIGINT, signal_handler)

		# Start JLinkGDBServer
		# FIXME Add way to check if the server is working and available
		jlink_cmd = [self.jlink_path + "/JLinkGDBServer", "-if", "SWD"]
		self.jlink = async_call(jlink_cmd, self.debug)
		time.sleep(1)

		# Connect to JLinkGDBServer SWO telnet server
		s = socket.socket()
		s.connect((self.jlink_host, self.jlink_port))

		f = open(self.output, 'w')

		# Reset the target
		if self.reset == "1":
			self.run_gdb("reset_target.gdb", 1)

		# Record PC Sampler traces
		self.run_gdb("trace_pc.gdb")

		while self.record:
			try:
				data = s.recv(1024)
				f.write(data)
			except socket.error:
				# FIXME
				print "Warning: Interrupted syscall"
		s.close()
		f.close()

		# Stop JLinkGDBServer
		recorder.jlink.send_signal(signal.SIGINT)

recorder = SWORecorder()

def main(argv):
	#Start a daemon to record traces
	daemon_runner = runner.DaemonRunner(recorder)
	daemon_runner.do_action()

if __name__ == "__main__":
	main(sys.argv[1:])