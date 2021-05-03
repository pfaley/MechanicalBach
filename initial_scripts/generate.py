import numpy as np
import pandas as pd
from music21 import converter, note, chord, instrument, stream
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, LSTM, Dropout
from tensorflow.keras.utils import to_categorical

# import data
path = '../maestro-v3.0.0/'

metadata = pd.read_csv(path + 'maestro-v3.0.0.csv')

notes = []

for filename in [metadata[metadata['year'] == 2018]['midi_filename'][0]]:
    file = path + filename
    midi = converter.parse(file)
    notes_to_parse = None

    notes_to_parse = midi.flat.notes

    for element in notes_to_parse:
        if isinstance(element, note.Note):
            notes.append(str(element.pitch))
        elif isinstance(element, chord.Chord):
            notes.append('.'.join(str(n) for n in element.normalOrder))

sequence_length = 100

pitchnames = sorted(set(item for item in notes))

n_vocab = len(pitchnames)

note_to_int = dict((note, number) for number, note in enumerate(pitchnames))

# setup network input and output
network_input = []
network_output = []

for i in range(0, len(notes) - sequence_length):
    sequence_in = notes[i:i + sequence_length]
    sequence_out = notes[i + sequence_length]
    network_input.append([note_to_int[char] for char in sequence_in])
    network_output.append(note_to_int[sequence_out])

n_patterns = len(network_input)

network_input = np.reshape(network_input, (n_patterns, sequence_length, 1))

# normalize input
network_input = network_input / float(n_vocab)

network_output = to_categorical(network_output)

# same model as in train

model = Sequential()
model.add(LSTM(512, input_shape=(network_input.shape[1], network_input.shape[2]), return_sequences=True))
model.add(Dropout(0.3))
model.add(LSTM(512, return_sequences=True))
model.add(Dropout(0.3))
model.add(LSTM(512))
model.add(Dense(256, activation='relu'))
model.add(Dropout(0.3))
model.add(Dense(n_vocab, activation='softmax'))


model.compile(loss='categorical_crossentropy', optimizer='rmsprop')

# loads weights
model.load_weights('../weights/lstm_initial-01-4.6047.hdf5')

# random starting index
start = np.random.randint(0, len(network_input)-1)

int_to_note = dict((number, note) for number, note in enumerate(pitchnames))
pattern = network_input[start]

prediction_output = []


nNotes = 500 # about 2 min
# generate notes
for note_index in range(nNotes):
    prediction_input = np.reshape(pattern, (1, len(pattern), 1))
    prediction_input = prediction_input / float(n_vocab)
    prediction = model.predict(prediction_input, verbose=0)
    index = np.argmax(prediction)
    result = int_to_note[index]
    prediction_output.append(result)
    pattern = np.append(pattern, index)
    pattern = pattern[1:len(pattern)]


# turn predictions into notes

offset = 0
output_notes = []
# create note and chord objects based on the values generated by the model
for pattern in prediction_output:
    # pattern is a chord
    if ('.' in pattern) or pattern.isdigit():
        notes_in_chord = pattern.split('.')
        notes = []
        for current_note in notes_in_chord:
            new_note = note.Note(int(current_note))
            new_note.storedInstrument = instrument.Piano()
            notes.append(new_note)
        new_chord = chord.Chord(notes)
        new_chord.offset = offset
        output_notes.append(new_chord)
    # pattern is a note
    else:
        new_note = note.Note(pattern)
        new_note.offset = offset
        new_note.storedInstrument = instrument.Piano()
        output_notes.append(new_note)
    # increase offset each iteration so that notes do not stack
    offset += 0.5

midi_stream = stream.Stream(output_notes)
midi_stream.write('midi', fp='test_output.mid')
