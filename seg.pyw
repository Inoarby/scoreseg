from music21 import *
import os
import subprocess
import csv
import argparse
import sys
import shutil
import tkinter as tk
from tkinter import messagebox
from tkinter import filedialog

musescore = r'C:\Program Files\MuseScore 4\bin\MuseScore4.exe'
anki_media_dir = r'C:\Users\InOarby\AppData\Roaming\Anki2\User 1\collection.media\\'

def divide_score_at_rehearsal_marks(file, output_dir):
    # Load the score
    score = converter.parse(file)
    # Only use the first part
    part = score.parts[0]

    score_name = score.metadata.title + " by " + score.metadata.composer
    score_name = score_name.replace(" ", "_")
    score_name = score_name.replace(".", "_")

    # Get the original clef, key signature, time signature, and tempo marking
    ori_clef = part.measure(1).clef
    ori_key = part.measure(1).keySignature
    ori_time = part.measure(1).timeSignature
    ori_tempo = part.measure(1).getElementsByClass('MetronomeMark')[0]
    print(ori_time, ori_tempo)

    #score = score.parts[0]
    # Initial setup
    measures = part.getElementsByClass('Measure')
    split_scores = []
    current_score = None

    # Iterate over the measures
    for measure in measures:
        measure.removeByClass(bar.Repeat)
        # Check if the measure has a rehearsal mark
        if any(isinstance(el, expressions.RehearsalMark) for el in measure.elements):
            # If a score is already in progress, add it to the list of split scores
            # Count the number of notes in the current score
            if current_score is not None and len(current_score.flat.getElementsByClass('Note')) > 5:
                split_scores.append(current_score)
            # Start a new score with the global information of the original score
            # Insert the original time signature and tempo marking if they are not present to the first measure
            if not any(isinstance(el, tempo.MetronomeMark) for el in measure.elements):
                measure.insert(0, ori_tempo)
            if not any(isinstance(el, meter.TimeSignature) for el in measure.elements):
                measure.insert(0, ori_time)
            current_score = part.cloneEmpty()
            current_score.insert(0, measure)
            current_score.insert(0, ori_clef)
            current_score.insert(0, ori_key)
        else:
            # If there is a current score, add the measure to it
            if current_score is not None:
                current_score.insert(measure.offset, measure)

    # Add the last score if it exists
    if current_score is not None and len(current_score.flat.getElementsByClass('Note')) > 5:
            split_scores.append(current_score)

    # Save the split scores to separate MusicXML files
    for i, split_score in enumerate(split_scores):
        split_score.write('musicxml', os.path.join(output_dir, f'{score_name}_{i+1}.musicxml'))

def convert_musicxml_to_svg(input_dir, output_dir):
    # Get a list of all MusicXML files in the input directory
    input_files = [f for f in os.listdir(input_dir) if f.endswith('.musicxml')]
    
    for input_file in input_files:
        # Define the input and output paths
        input_path = os.path.join(input_dir, input_file)
        output_path = os.path.join(output_dir, f'{os.path.splitext(input_file)[0]}.svg')
        
        # Convert the MusicXML file to PNG using MuseScore4 command-line interface
        subprocess.run([musescore, '-o', output_path, input_path, '-T', '100'])

def convert_musicxml_to_mp3(input_dir, output_dir):
    # Get a list of all MusicXML files in the input directory
    input_files = [f for f in os.listdir(input_dir) if f.endswith('.musicxml')]
    
    for input_file in input_files:
        # Define the input and output paths
        input_path = os.path.join(input_dir, input_file)
        output_path = os.path.join(output_dir, f'{os.path.splitext(input_file)[0]}.mp3')
        
        # Convert the MusicXML file to PNG using MuseScore4 command-line interface
        subprocess.run([musescore, '-o', output_path, input_path])

def convert_musescore_to_musicxml(file):
    # Define the output path
    output_file = os.path.splitext(file)[0] + '.musicxml'
    output_path = os.path.join(os.path.dirname(file), output_file)
    
    # Convert the MuseScore file to MusicXML using MuseScore4 command-line interface
    subprocess.run([musescore, '-o', output_path, file])
    
    return output_path

def write_anki_import_file(media_list, output_dir):
    with open(os.path.join(output_dir, 'anki_import.txt'), 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, delimiter=';')
        for m in media_list:  # For each set of MusicXML, PNG, and MP3 files
            front = f'<img src="{m}.svg">'
            back = f'[sound:{m}.mp3]'
            writer.writerow([front, back, f'{m}'])  # The third column is the card tag

def copy_media_to_anki(svg_dir, mp3_dir):
    # Get a list of all SVG and MP3 files in the input directories
    svg_files = [f for f in os.listdir(svg_dir) if f.endswith('.svg')]
    mp3_files = [f for f in os.listdir(mp3_dir) if f.endswith('.mp3')]

    # Copy the SVG files to the Anki media directory
    for svg_file in svg_files:
        svg_path = os.path.join(svg_dir, svg_file)
        shutil.copy(svg_path, anki_media_dir)
    
    # Copy the MP3 files to the Anki media directory
    for mp3_file in mp3_files:
        mp3_path = os.path.join(mp3_dir, mp3_file)
        shutil.copy(mp3_path, anki_media_dir)

def main(score, div, to_svg, to_mp3, anki_import, copy_media):
    # Define the input and output directories
    working_dir = os.path.dirname(score)
    seg_dir = working_dir + r"\segment_dir"
    mp3_dir = working_dir + r"\mp3_dir"
    svg_dir = working_dir + r"\svg_dir"

    # Make the output directories if they don't exist
    try:
        if not os.path.exists(seg_dir):
            os.makedirs(seg_dir)
        if not os.path.exists(mp3_dir):
            os.makedirs(mp3_dir)
        if not os.path.exists(svg_dir):
            os.makedirs(svg_dir)
    except OSError:
        print('Error: Creating directory. ' + seg_dir)
        print('Error: Creating directory. ' + mp3_dir)
        print('Error: Creating directory. ' + svg_dir)
        sys.exit()

    # Convert score to MusicXML if it ends with .mscz
    if score.endswith('.mscz'):
        print('Converting MuseScore file to MusicXML.')
        score = convert_musescore_to_musicxml(score)
    
    # Exits if the score is not a MusicXML file
    if not score.endswith('.musicxml'):
        sys.exit('The score must be a MusicXML file of a MuseScore file')

    # Divide the score at rehearsal marks
    if div:
        print('Dividing score at rehearsal marks.')
        divide_score_at_rehearsal_marks(score, seg_dir)

    # Convert the MusicXML files to SVG and MP3
    if to_svg:
        print('Converting MusicXML files to SVG.')
        convert_musicxml_to_svg(seg_dir, svg_dir)
    if to_mp3:
        print('Converting MusicXML files to MP3.')
        convert_musicxml_to_mp3(seg_dir, mp3_dir)

    # Create a list of all the media files
    media_list = [os.path.splitext(f)[0] for f in os.listdir(seg_dir)]

    # Write the Anki import file
    if anki_import:
        print('Writing Anki import file.')
        write_anki_import_file(media_list, working_dir)

    # Copy the media files to the Anki media directory
    if copy_media:
        print('Copying media files to Anki media directory.')
        copy_media_to_anki(svg_dir, mp3_dir)

if __name__ == '__main__':
    #parser = argparse.ArgumentParser(description="Split score and make them into Anki cards")
    #parser.add_argument("-s", "--score", help="The path to the score", required=True)
    #args = parser.parse_args()

    #main(args.score)

    # Create the main window
    root = tk.Tk()

    # Add a title
    root.title("Score to Anki")

    # Variables to hold inputs
    score_path = tk.StringVar()
    div_bool = tk.BooleanVar(value=True)
    svg_bool = tk.BooleanVar(value=True)
    mp3_bool = tk.BooleanVar(value=True)
    import_bool = tk.BooleanVar(value=False)
    copy_bool = tk.BooleanVar(value=False)

    # Function to open file dialog and set filepath
    def open_file():
        filepath = filedialog.askopenfilename()
        score_path.set(filepath)

    # Function to call main with inputs
    def call_main():
        try:
            result = main(score_path.get(), div_bool.get(), svg_bool.get(), mp3_bool.get(), import_bool.get(), copy_bool.get())
            messagebox.showinfo("Result", str(result))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # Create and add widgets
    tk.Label(root, text="File: ").grid(row=0, column=0, sticky='w')
    tk.Entry(root, textvariable=score_path, state='readonly').grid(row=0, column=1, sticky='w')
    tk.Button(root, text="Browse", command=open_file).grid(row=0, column=2, sticky='w')
    tk.Checkbutton(root, text="Divide at rehearsal", variable=div_bool).grid(row=1, column=0, sticky='w')
    tk.Checkbutton(root, text="Convert to svg", variable=svg_bool).grid(row=2, column=0, sticky='w')
    tk.Checkbutton(root, text="Convert to mp3", variable=mp3_bool).grid(row=3, column=0, sticky='w')
    tk.Checkbutton(root, text="Generate anki import", variable=import_bool).grid(row=4, column=0, sticky='w')
    tk.Checkbutton(root, text="Copy to media", variable=copy_bool).grid(row=5, column=0, sticky='w')
    tk.Button(root, text="Run", command=call_main).grid(row=6, column=0)

    # Start the event loop
    root.mainloop()