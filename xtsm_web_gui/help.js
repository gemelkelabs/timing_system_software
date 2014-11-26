// JavaScript Document

//Global variables to hold help links

python_console_help_text="<table><td><b>Help with Python Console:</b><ul><li>&uarr;/&darr;:  previous/next command<li>ctrl-&rarr; right arrow:  autocomplete from previous<li>enter:  submit command<li>end/home:  last/first command in buffer<li>escape:  abort entry<li> &amp;-character:  separator for multiple commands per line <li>$-character:  continue command to next line</td><td></td><td></td></tr></table>";

help_fields = new Object;
help_fields.available_fields = [];
help_fields.quick_descript = [];
help_fields.links = [];

help_fields.available_fields.push(	'PreParseInstructions');
help_fields.quick_descript.push(	'Commands for the parser to execute before undergoing its parsing routine.');
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/PreParseInstructions_(Timing_Element)');

help_fields.available_fields.push(	'PostParseInstructions');
help_fields.quick_descript.push(	'Commands for the parser to execute after undergoing its parsing routine.');
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/PostParseInstructions_(Timing_Element)');

help_fields.available_fields.push(	'ParserCommand');
help_fields.quick_descript.push(	'An individual command. Consists of a command name and (optionally) values.');
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/ParserCommand_(Timing_Element)');

help_fields.available_fields.push(	'Enabled');
help_fields.quick_descript.push(	'A zero in this field will effectively remove this element from the experiment without deleting its entries.  All other values (including no value) will indicate an active element.');
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/Enabled_(Timing_Element)');

help_fields.available_fields.push(	'TimingData');
help_fields.quick_descript.push(	'Timing data is returned from the parser after determining the output values in an interval.');
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/TimingData_(Timing_Element)');

help_fields.available_fields.push(	'ResolutionBits');
help_fields.quick_descript.push(	'The number of bits of resolution for channels in this timing group.  For digital channels, choose 1.');
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/ResolutionBits_(Timing_Element)');

help_fields.available_fields.push(	'Range');
help_fields.quick_descript.push(	'The voltage range of a given DAQ. For example, the PXIe-6733 can output a voltage between -10V and +10V, giving a range of 20V');
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/Range_(Timing_Element)');

help_fields.available_fields.push(	'DAQCalibration');
help_fields.quick_descript.push(	'The scale calibration constant stored on the EEPROM of a given DAQ. The DAQCalibration value is a number of steps to produce one volt, and depends on the bit resolution and range of the DAQ.');
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/DAQCalibration_(Timing_Element)');

help_fields.available_fields.push(	'ChannelCount');
help_fields.quick_descript.push(	'The number of channels in this group.');
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/ChannelCount_(Timing_Element)');

help_fields.available_fields.push(	'GroupNumber');
help_fields.quick_descript.push(	'The timing group number is the index all channels in this group must declare to be included in the clocking and output table construction performed by the parser.');
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/GroupNumber_(Timing_Element)');

help_fields.available_fields.push(	'ClockedBy');
help_fields.quick_descript.push(	'The name of the channel this group is clocked by - this channel must be defined in the channel map.  The parser will add edges to this channel corresponding to any time an update is necessary on a channel in this timing group.');
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/ClockedBy_(Timing_Element)');

help_fields.available_fields.push(	'TimingGroupData');
help_fields.quick_descript.push(	'The timing group data node contains information common to a group of channels clocked by a common source - typically a timing group is a set of channels on the same physical output card. The parser will generate a table of output values for this group, and a corresponding triggering pulse sequence for the clocking channel.');
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/TimingGroupData_(Timing_Element)');

help_fields.available_fields.push(	'MaxDuration');
help_fields.quick_descript.push(	'The maximum duration this channel should remain high. It is not yet implemented in the IDL parser.');
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/MaxDuration_(Timing_Element)');

help_fields.available_fields.push(	'MaxTriggers');
help_fields.quick_descript.push(	'The maximum number of rises this channel should have. It is not yet implemented in the IDL parser.');
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/MaxTriggers_(Timing_Element)');

help_fields.available_fields.push(	'MaxDuty');
help_fields.quick_descript.push(	'The maximum duty cyle this channel should use. It is not yet implemented in the IDL parser.');
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/MaxDuty_(Timing_Element)');

help_fields.available_fields.push(	'MaxValue');
help_fields.quick_descript.push(	'The maximum value (in volts) this channel should ever put out - larger values will be clipped.');
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/MaxValue_(Timing_Element)');

help_fields.available_fields.push(	'MinValue');
help_fields.quick_descript.push(	'The minimum value (in volts) this channel should ever put out - smaller values will be clipped.');
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/MinValue_(Timing_Element)');

help_fields.available_fields.push(	'Calibration');
help_fields.quick_descript.push(	'This calibration expression is used to convert the value a channel is given inside sequences to an output voltage.  It is not yet implemented in the IDL parser.');
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/Calibration_(Timing_Element)');

help_fields.available_fields.push(	'HoldingValue');
help_fields.quick_descript.push(	'The holding value is the physical output value (in Volts) this channel should be held at when no sequence is being run or no edge or interval defines its value.');
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/HoldingValue_(Timing_Element)');

help_fields.available_fields.push(	'Group');
help_fields.quick_descript.push(	'An optional group name.');
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/Group_(Timing_Element)');

help_fields.available_fields.push(	'ConnectsTo');
help_fields.quick_descript.push(	'Use this to reference the signal name of the hardware device this channel is physically connected to.');
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/ConnectsTo_(Timing_Element)');

help_fields.available_fields.push(	'TimingGroupIndex');
help_fields.quick_descript.push(	'The index of this channel within its timing group (typically this is the channel number on a given card).');
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/TimingGroupIndex_(Timing_Element)');

help_fields.available_fields.push(	'TimingGroup');
help_fields.quick_descript.push(	'A timing group defines a set of channels who are clocked (updated) by a common source.  In general, hardware channels belonging to the same card will be clocked together.');
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/TimingGroup_(Timing_Element)');

help_fields.available_fields.push(	'Timing Channel');
help_fields.quick_descript.push(	'The timing channel is simply a name for a given hardware channel.');
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/Timing Channel_(Timing_Element)');

help_fields.available_fields.push(	'Channel');
help_fields.quick_descript.push(	'A channel refers to a single signal of control');
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/Channel_(Timing_Element)');

help_fields.available_fields.push(	'ChannelMap');
help_fields.quick_descript.push(	'The Channel Map contains data about the physical connection of channels to hardware elements and defines calibration data for each channel.  As hardware changes are made, this segment should be updated.');
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/ChannelMap_(Timing_Element)');

help_fields.available_fields.push(	'ClockPeriod');
help_fields.quick_descript.push(	'Sampling period (ms).');
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/ClockPeriod_(Timing_Element)');

help_fields.available_fields.push(	'Parameter');
help_fields.quick_descript.push(	'Parameters may be defined for use in formulas in IDL-parsed fields. They are themselves parsed by IDL. Their scope is limited to siblings and child nodes.');
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/Parameter_(Timing_Element)');

help_fields.available_fields.push(	'Comments');
help_fields.quick_descript.push(	'Include comments here - you may include standard html markup tags in edit mode which will be visible in view mode.');
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/Comments_(Timing_Element)');

help_fields.available_fields.push(	'Description');
help_fields.quick_descript.push(	'Use this field to provide a description of this element - you may include standard html markup tags in edit mode which will be visible in view mode.');
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/Description_(Timing_Element)');

help_fields.available_fields.push(	'Interval');
help_fields.quick_descript.push(	'Intervals define a period of time in which an output is to occur on some control channel');
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/Interval_(Timing_Element)');

help_fields.available_fields.push(	'SubSequence');
help_fields.quick_descript.push(	'SubSequences are collections of edges, intervals, etc... related to a common purpose.  All child nodes of a subsequence are referenced to its start time, and have access to its parameters and those of its elders.');
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/SubSequence_(Timing_Element)');

help_fields.available_fields.push(	'Sequence');
help_fields.quick_descript.push(	'One experiment sequence is run per shot number - it is chosen by the SequenceSelector Node.');
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/Sequence_(Timing_Element)');

help_fields.available_fields.push(	'EndTime');
help_fields.quick_descript.push(	'The time in milliseconds the sequence should end - it is NOT parsed by IDL, will default to 10000 (10 seconds), and cannot be longer than 100000');
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/EndTime_(Timing_Element)');

help_fields.available_fields.push(	'Time');
help_fields.quick_descript.push(	'The time in milliseconds this edge should occur - it is relative to parent subsequence time(s), and is parsed by IDL. ');
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/Time_(Timing_Element)');

help_fields.available_fields.push(	'End');
help_fields.quick_descript.push(	'The time in milliseconds this interval should end - it is relative to parent subsequence time(s), and is parsed by IDL.');
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/End_(Timing_Element)');

help_fields.available_fields.push(	'Start');
help_fields.quick_descript.push(	'The time in milliseconds this interval should start - it is relative to parent subsequence time(s), and is parsed by IDL.');
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/Start_(Timing_Element)');

help_fields.available_fields.push(	'Value');
help_fields.quick_descript.push(	'The value to output. If in a channel, it will be parsed by IDL and is subject to modification by channel definition.');
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/Value_(Timing_Element)');

help_fields.available_fields.push(	'TResolution');
help_fields.quick_descript.push(	'The time interval in milliseconds desired between output samples');
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/TResolution_(Timing_Element)');

help_fields.available_fields.push(	'VResolution');
help_fields.quick_descript.push(	'The minimum step size desired in the output voltage.');
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/VResolution_(Timing_Element)');

help_fields.available_fields.push(	'Values');
help_fields.quick_descript.push(	'An IDL-syntax list of values to output.  If this is a sampling input interval, type "SAMPLE".');
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/Values_(Timing_Element)');

help_fields.available_fields.push(	'Times');
help_fields.quick_descript.push(	'An IDL-syntax list of times to update output in this interval. Alternately, you may click icon to the right, and enter a desired time-resolution at which to evenly distribute updates in this interval. ');
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/Times_(Timing_Element)');

help_fields.available_fields.push(	'SerialGroup');
help_fields.quick_descript.push(	'A serial group is a set of three digital signals used to transfer data on a serial communications line.');
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/SerialGroup_(Timing_Element)');

help_fields.available_fields.push(	'ClockChannel');
help_fields.quick_descript.push(	'The clock channel specifies what channel is to be used to clock data transfer from the data line.');
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/ClockChannel_(Timing_Element)');

help_fields.available_fields.push(	'DataChannel');
help_fields.quick_descript.push(	'The data channel specifies what channel is to be used as data.');
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/DataChannel_(Timing_Element)');

help_fields.available_fields.push(	'UpdateChannel');
help_fields.quick_descript.push(	'The update channel specifies what channel is to be used as an update strobe.');
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/UpdateChannel_(Timing_Element)');

help_fields.available_fields.push(	'ClockPolarity');
help_fields.quick_descript.push(	"Specifies whether data should be read from the data line on the clock's rising or falling edge.  Acceptable values:  Rising Edge or Falling Edge");
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/ClockPolarity_(Timing_Element)');

help_fields.available_fields.push(	'TimeBase');
help_fields.quick_descript.push(	"The period of the clock pulses.");
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/TimeBase_(Timing_Element)');

help_fields.available_fields.push(	'SerialTransfer');
help_fields.quick_descript.push(	"A serial transfer is a string of digital data ouput on a serial group.");
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/SerialTransfer_(Timing_Element)');

help_fields.available_fields.push(	'OnSerialGroup');
help_fields.quick_descript.push(	"The name of the serial group to output data on.");
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/OnSerialGroup_(Timing_Element)');

help_fields.available_fields.push(	'DataString');
help_fields.quick_descript.push(	"A string of bits to transfer - this must an IDL-compatible syntax which evaluates to an array of 1's and 0's.");
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/OnSerialGroup_(Timing_Element)');

help_fields.available_fields.push(	'UpdateTime');
help_fields.quick_descript.push(	"The time at which the serial data transfer is signalled complete on the update strobe channel.");
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/UpdateTime_(Timing_Element)');

help_fields.available_fields.push(	'Direction');
help_fields.quick_descript.push(	'Specifies whether a timing group\'s function is input or output. Output is default. ');
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/Direction_(Timing_Element)');

help_fields.available_fields.push(	'ParserInstructions');
help_fields.quick_descript.push(	'Special fields to be analyzed by the parser. ');
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/ParserInstructions_(Timing_Element)');

help_fields.available_fields.push(	'RepresentAsInteger');
help_fields.quick_descript.push(	'Specifies whether all channels will be represented as a single integer. Default is "no" - all channels are represented separately. ');
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/RepresentAsInteger_(Timing_Element)');

help_fields.available_fields.push(	'Pulser');
help_fields.quick_descript.push(	'Specifies whether a clock pulses automatically ("yes") or whether it clocks on rise/fall ("no"). Default is "no", in which case the group being clocked should have an ActiveClockEdge field. ');
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/Pulser_(Timing_Element)');

help_fields.available_fields.push(	'SparseControlArray');
help_fields.quick_descript.push(	'Specifies whether a timing group requires a sparse-to-dense conversion. Default is "yes". ');
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/Pulser_(Timing_Element)');

help_fields.available_fields.push(	'ActiveClockEdge');
help_fields.quick_descript.push(	'Specifies whether a timing group is clocked on "rise" or "fall" of the clocking element. Rise is default. ');
help_fields.links.push(				'https://amo.phys.psu.edu/GemelkeLabWiki/index.php/ActiveClockEdge_(Timing_Element)');
