# -*- coding: utf-8 -*-
"""
Audio Training Laboratory Module for EchoLearn
Handles audio recording, processing, and visualization for ML training data
"""

import streamlit as st
import numpy as np
import librosa
import librosa.display
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import sounddevice as sd
import soundfile as sf
import io
import os
import datetime
import pandas as pd
from pathlib import Path
import time

class AudioTrainingLab:
    """Audio Training Laboratory for ML model training data collection"""
    
    def __init__(self):
        self.sample_rate = 44100
        self.channels = 1
        self.dtype = 'float32'
        self.recordings_dir = Path("audio_recordings")
        self.recordings_dir.mkdir(exist_ok=True)
        
        # Initialize session state for audio lab
        if 'audio_lab_recordings' not in st.session_state:
            st.session_state.audio_lab_recordings = []
        if 'current_recording' not in st.session_state:
            st.session_state.current_recording = None
        if 'recording_in_progress' not in st.session_state:
            st.session_state.recording_in_progress = False
    
    def display_audio_lab_interface(self):
        """Main interface for the Audio Training Lab"""
        st.header("🎙️ Audio Training Laboratory")
        st.markdown("**Collect and analyze audio data for machine learning model training**")
        
        # Create tabs for different functionalities
        tab1, tab2, tab3, tab4 = st.tabs([
            "🎤 Recording Studio", 
            "📊 Real-time Analysis", 
            "📁 Recordings Library", 
            "🔧 ML Data Export"
        ])
        
        with tab1:
            self.display_recording_studio()
        
        with tab2:
            self.display_realtime_analysis()
        
        with tab3:
            self.display_recordings_library()
        
        with tab4:
            self.display_ml_data_export()
    
    def display_recording_studio(self):
        """Recording studio interface"""
        st.subheader("🎤 Recording Studio")
        
        # Recording controls
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            # Recording metadata
            recording_name = st.text_input(
                "Recording Name:", 
                value=f"recording_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            
            speaker_name = st.text_input("Speaker Name:", value="")
            
            recording_type = st.selectbox(
                "Recording Type:",
                ["Question Answer", "Reading Passage", "Conversation", "Phonetics", "Other"]
            )
            
            content_description = st.text_area(
                "Content Description:", 
                placeholder="Describe what will be recorded..."
            )
        
        with col2:
            # Recording settings
            st.markdown("**Settings**")
            duration = st.slider("Duration (seconds):", 1, 60, 10)
            
            # Quality settings
            quality = st.selectbox("Quality:", ["Standard (44.1kHz)", "High (48kHz)", "CD Quality (44.1kHz)"])
            if quality == "High (48kHz)":
                self.sample_rate = 48000
            else:
                self.sample_rate = 44100
        
        with col3:
            # Recording status
            st.markdown("**Status**")
            if st.session_state.recording_in_progress:
                st.error("🔴 Recording...")
                if st.button("⏹️ Stop Recording"):
                    self.stop_recording()
            else:
                st.success("⚪ Ready")
                if st.button("🎙️ Start Recording"):
                    if recording_name and speaker_name:
                        self.start_recording(duration, {
                            'name': recording_name,
                            'speaker': speaker_name,
                            'type': recording_type,
                            'description': content_description
                        })
                    else:
                        st.error("Please fill in recording name and speaker name")
        
        # Real-time recording visualization
        if st.session_state.recording_in_progress:
            self.display_live_recording_viz()
        
        # Display current recording if available
        if st.session_state.current_recording is not None:
            self.display_current_recording_analysis()
    
    def display_realtime_analysis(self):
        """Real-time audio analysis interface"""
        st.subheader("📊 Real-time Audio Analysis")
        
        # Quick record button for analysis
        col1, col2 = st.columns([1, 3])
        
        with col1:
            if st.button("🎙️ Quick Record (5s)"):
                audio_data = self.quick_record(5)
                if audio_data is not None:
                    st.session_state.analysis_audio = audio_data
        
        with col2:
            # Upload audio file for analysis
            uploaded_file = st.file_uploader(
                "Or upload an audio file:", 
                type=['wav', 'mp3', 'flac', 'ogg']
            )
            if uploaded_file is not None:
                try:
                    audio_data, sr = librosa.load(uploaded_file, sr=self.sample_rate)
                    st.session_state.analysis_audio = audio_data
                    st.success("✅ Audio file loaded successfully!")
                except Exception as e:
                    st.error(f"Error loading audio file: {str(e)}")
        
        # Analysis visualization
        if hasattr(st.session_state, 'analysis_audio'):
            self.display_comprehensive_analysis(st.session_state.analysis_audio)
    
    def display_recordings_library(self):
        """Recordings library interface"""
        st.subheader("📁 Recordings Library")
        
        if not st.session_state.audio_lab_recordings:
            st.info("No recordings yet. Go to Recording Studio to create your first recording!")
            return
        
        # Display recordings in a table
        recordings_data = []
        for i, recording in enumerate(st.session_state.audio_lab_recordings):
            recordings_data.append({
                'ID': i,
                'Name': recording['metadata']['name'],
                'Speaker': recording['metadata']['speaker'],
                'Type': recording['metadata']['type'],
                'Duration': f"{len(recording['audio']) / self.sample_rate:.2f}s",
                'Timestamp': recording['timestamp'],
                'File Size': f"{len(recording['audio']) * 4 / 1024:.1f} KB"  # float32 = 4 bytes
            })
        
        df = pd.DataFrame(recordings_data)
        
        # Selection and controls
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            selected_recording = st.selectbox(
                "Select Recording:", 
                options=range(len(st.session_state.audio_lab_recordings)),
                format_func=lambda x: f"{recordings_data[x]['Name']} - {recordings_data[x]['Speaker']}"
            )
        
        with col2:
            if st.button("🎵 Play Selected"):
                self.play_recording(selected_recording)
        
        with col3:
            if st.button("📊 Analyze Selected"):
                recording = st.session_state.audio_lab_recordings[selected_recording]
                st.session_state.analysis_audio = recording['audio']
        
        # Display recordings table
        st.dataframe(df, use_container_width=True)
        
        # Display selected recording details
        if selected_recording is not None:
            self.display_recording_details(selected_recording)
    
    def display_ml_data_export(self):
        """ML data export interface"""
        st.subheader("🔧 ML Data Export")
        
        if not st.session_state.audio_lab_recordings:
            st.info("No recordings available for export. Record some audio first!")
            return
        
        st.markdown("**Export Options**")
        
        # Export format selection
        export_format = st.selectbox(
            "Export Format:",
            ["CSV (Features)", "NumPy Arrays", "JSON (Full Data)", "WAV Files", "Mel Spectrograms"]
        )
        
        # Feature extraction options
        if export_format in ["CSV (Features)", "NumPy Arrays"]:
            st.markdown("**Feature Extraction Settings**")
            
            feature_options = st.multiselect(
                "Select Features to Extract:",
                [
                    "MFCC (Mel-frequency cepstral coefficients)",
                    "Spectral Centroid",
                    "Spectral Rolloff",
                    "Zero Crossing Rate",
                    "Chroma Features",
                    "Spectral Contrast",
                    "Tonnetz",
                    "Fundamental Frequency (F0)",
                    "Energy/RMS",
                    "Spectral Flatness"
                ],
                default=["MFCC (Mel-frequency cepstral coefficients)", "Spectral Centroid", "Energy/RMS"]
            )
        
        # Export controls
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📤 Export Selected Data"):
                self.export_ml_data(export_format, feature_options if 'feature_options' in locals() else None)
        
        with col2:
            if st.button("📋 Generate Dataset Summary"):
                self.generate_dataset_summary()
    
    def start_recording(self, duration, metadata):
        """Start audio recording"""
        try:
            st.session_state.recording_in_progress = True
            
            # Record audio
            with st.spinner(f"Recording for {duration} seconds..."):
                audio_data = sd.rec(
                    int(duration * self.sample_rate),
                    samplerate=self.sample_rate,
                    channels=self.channels,
                    dtype=self.dtype
                )
                
                # Progress bar
                progress_bar = st.progress(0)
                for i in range(duration):
                    time.sleep(1)
                    progress_bar.progress((i + 1) / duration)
                
                sd.wait()  # Wait until recording is finished
            
            # Store recording
            recording = {
                'audio': audio_data.flatten(),
                'sample_rate': self.sample_rate,
                'metadata': metadata,
                'timestamp': datetime.datetime.now().isoformat()
            }
            
            st.session_state.audio_lab_recordings.append(recording)
            st.session_state.current_recording = audio_data.flatten()
            st.session_state.recording_in_progress = False
            
            st.success(f"✅ Recording '{metadata['name']}' completed!")
            
            # Save to file
            filename = f"{metadata['name']}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
            filepath = self.recordings_dir / filename
            sf.write(filepath, audio_data, self.sample_rate)
            
        except Exception as e:
            st.session_state.recording_in_progress = False
            st.error(f"Recording failed: {str(e)}")
    
    def stop_recording(self):
        """Stop current recording"""
        sd.stop()
        st.session_state.recording_in_progress = False
        st.success("Recording stopped")
    
    def quick_record(self, duration):
        """Quick recording for analysis"""
        try:
            with st.spinner(f"Recording {duration} seconds for analysis..."):
                audio_data = sd.rec(
                    int(duration * self.sample_rate),
                    samplerate=self.sample_rate,
                    channels=self.channels,
                    dtype=self.dtype
                )
                sd.wait()
            
            return audio_data.flatten()
        except Exception as e:
            st.error(f"Quick recording failed: {str(e)}")
            return None
    
    def display_comprehensive_analysis(self, audio_data):
        """Display comprehensive audio analysis"""
        st.markdown("### 📊 Audio Analysis Results")
        
        # Basic info
        duration = len(audio_data) / self.sample_rate
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Duration", f"{duration:.2f}s")
        col2.metric("Sample Rate", f"{self.sample_rate} Hz")
        col3.metric("Samples", len(audio_data))
        col4.metric("Max Amplitude", f"{np.max(np.abs(audio_data)):.3f}")
        
        # Waveform
        st.markdown("#### 🌊 Waveform")
        fig_wave = self.create_waveform_plot(audio_data)
        st.plotly_chart(fig_wave, use_container_width=True)
        
        # Spectrogram
        st.markdown("#### 🎨 Spectrogram")
        fig_spec = self.create_spectrogram_plot(audio_data)
        st.plotly_chart(fig_spec, use_container_width=True)
        
        # Feature analysis
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📈 Spectral Features")
            features = self.extract_spectral_features(audio_data)
            
            # Display features as metrics
            st.metric("Spectral Centroid (Hz)", f"{features['spectral_centroid']:.1f}")
            st.metric("Spectral Rolloff (Hz)", f"{features['spectral_rolloff']:.1f}")
            st.metric("Zero Crossing Rate", f"{features['zcr']:.4f}")
            st.metric("RMS Energy", f"{features['rms']:.4f}")
        
        with col2:
            st.markdown("#### 🎵 MFCC Features")
            mfcc = librosa.feature.mfcc(y=audio_data, sr=self.sample_rate, n_mfcc=13)
            
            # MFCC heatmap
            fig_mfcc = px.imshow(
                mfcc,
                title="MFCC Coefficients",
                labels={'x': 'Time Frame', 'y': 'MFCC Coefficient', 'color': 'Value'},
                aspect='auto'
            )
            st.plotly_chart(fig_mfcc, use_container_width=True)
        
        # Frequency analysis
        st.markdown("#### 🔊 Frequency Analysis")
        fig_fft = self.create_fft_plot(audio_data)
        st.plotly_chart(fig_fft, use_container_width=True)
    
    def create_waveform_plot(self, audio_data):
        """Create waveform visualization"""
        time_axis = np.linspace(0, len(audio_data) / self.sample_rate, len(audio_data))
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=time_axis,
            y=audio_data,
            mode='lines',
            name='Waveform',
            line=dict(color='blue', width=1)
        ))
        
        fig.update_layout(
            title="Audio Waveform",
            xaxis_title="Time (seconds)",
            yaxis_title="Amplitude",
            height=300
        )
        
        return fig
    
    def create_spectrogram_plot(self, audio_data):
        """Create spectrogram visualization"""
        # Compute spectrogram
        D = librosa.stft(audio_data)
        S_db = librosa.amplitude_to_db(np.abs(D), ref=np.max)
        
        # Create time and frequency axes
        times = librosa.frames_to_time(np.arange(S_db.shape[1]), sr=self.sample_rate)
        freqs = librosa.fft_frequencies(sr=self.sample_rate)
        
        fig = go.Figure(data=go.Heatmap(
            z=S_db,
            x=times,
            y=freqs,
            colorscale='Viridis',
            colorbar=dict(title="dB")
        ))
        
        fig.update_layout(
            title="Spectrogram",
            xaxis_title="Time (seconds)",
            yaxis_title="Frequency (Hz)",
            height=400
        )
        
        return fig
    
    def create_fft_plot(self, audio_data):
        """Create FFT frequency analysis plot"""
        # Compute FFT
        fft = np.fft.fft(audio_data)
        freqs = np.fft.fftfreq(len(audio_data), 1/self.sample_rate)
        magnitude = np.abs(fft)
        
        # Only plot positive frequencies
        positive_freqs = freqs[:len(freqs)//2]
        positive_magnitude = magnitude[:len(magnitude)//2]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=positive_freqs,
            y=positive_magnitude,
            mode='lines',
            name='Frequency Spectrum',
            line=dict(color='red')
        ))
        
        fig.update_layout(
            title="Frequency Spectrum (FFT)",
            xaxis_title="Frequency (Hz)",
            yaxis_title="Magnitude",
            height=300
        )
        
        return fig
    
    def extract_spectral_features(self, audio_data):
        """Extract spectral features from audio"""
        # Spectral centroid
        spectral_centroid = librosa.feature.spectral_centroid(y=audio_data, sr=self.sample_rate)[0]
        
        # Spectral rolloff
        spectral_rolloff = librosa.feature.spectral_rolloff(y=audio_data, sr=self.sample_rate)[0]
        
        # Zero crossing rate
        zcr = librosa.feature.zero_crossing_rate(audio_data)[0]
        
        # RMS energy
        rms = librosa.feature.rms(y=audio_data)[0]
        
        return {
            'spectral_centroid': np.mean(spectral_centroid),
            'spectral_rolloff': np.mean(spectral_rolloff),
            'zcr': np.mean(zcr),
            'rms': np.mean(rms)
        }
    
    def display_current_recording_analysis(self):
        """Display analysis of current recording"""
        st.markdown("### 🎯 Current Recording Analysis")
        
        if st.session_state.current_recording is not None:
            self.display_comprehensive_analysis(st.session_state.current_recording)
        else:
            st.info("No current recording to analyze")
    
    def display_recording_details(self, recording_idx):
        """Display details of selected recording"""
        recording = st.session_state.audio_lab_recordings[recording_idx]
        
        st.markdown(f"### 📄 Recording Details: {recording['metadata']['name']}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Metadata**")
            st.write(f"**Speaker:** {recording['metadata']['speaker']}")
            st.write(f"**Type:** {recording['metadata']['type']}")
            st.write(f"**Timestamp:** {recording['timestamp']}")
            st.write(f"**Duration:** {len(recording['audio']) / recording['sample_rate']:.2f}s")
        
        with col2:
            st.markdown("**Description**")
            st.write(recording['metadata']['description'])
        
        # Quick analysis
        if st.button(f"🔍 Analyze Recording {recording_idx}"):
            st.session_state.analysis_audio = recording['audio']
            self.display_comprehensive_analysis(recording['audio'])
    
    def play_recording(self, recording_idx):
        """Play selected recording"""
        try:
            recording = st.session_state.audio_lab_recordings[recording_idx]
            st.audio(recording['audio'], sample_rate=recording['sample_rate'])
            st.success(f"Playing: {recording['metadata']['name']}")
        except Exception as e:
            st.error(f"Error playing recording: {str(e)}")
    
    def export_ml_data(self, format_type, features=None):
        """Export ML training data"""
        if not st.session_state.audio_lab_recordings:
            st.error("No recordings to export!")
            return
        
        try:
            if format_type == "CSV (Features)":
                self.export_features_csv(features)
            elif format_type == "NumPy Arrays":
                self.export_numpy_arrays()
            elif format_type == "JSON (Full Data)":
                self.export_json_data()
            elif format_type == "WAV Files":
                self.export_wav_files()
            elif format_type == "Mel Spectrograms":
                self.export_mel_spectrograms()
                
            st.success(f"✅ Data exported successfully in {format_type} format!")
            
        except Exception as e:
            st.error(f"Export failed: {str(e)}")
    
    def export_features_csv(self, selected_features):
        """Export extracted features as CSV"""
        features_data = []
        
        for i, recording in enumerate(st.session_state.audio_lab_recordings):
            audio = recording['audio']
            features = {'recording_id': i}
            features.update(recording['metadata'])
            
            # Extract selected features
            if "MFCC (Mel-frequency cepstral coefficients)" in selected_features:
                mfcc = librosa.feature.mfcc(y=audio, sr=self.sample_rate, n_mfcc=13)
                for j in range(13):
                    features[f'mfcc_{j}'] = np.mean(mfcc[j])
            
            if "Spectral Centroid" in selected_features:
                features['spectral_centroid'] = np.mean(
                    librosa.feature.spectral_centroid(y=audio, sr=self.sample_rate)
                )
            
            if "Energy/RMS" in selected_features:
                features['rms_energy'] = np.mean(
                    librosa.feature.rms(y=audio)
                )
            
            # Add more features as needed...
            
            features_data.append(features)
        
        df = pd.DataFrame(features_data)
        
        # Create download
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        
        st.download_button(
            label="📥 Download Features CSV",
            data=csv_buffer.getvalue(),
            file_name=f"audio_features_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    def generate_dataset_summary(self):
        """Generate and display dataset summary"""
        if not st.session_state.audio_lab_recordings:
            st.error("No recordings available!")
            return
        
        st.markdown("### 📊 Dataset Summary")
        
        # Basic statistics
        total_recordings = len(st.session_state.audio_lab_recordings)
        total_duration = sum(len(r['audio']) / r['sample_rate'] for r in st.session_state.audio_lab_recordings)
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Recordings", total_recordings)
        col2.metric("Total Duration", f"{total_duration:.1f}s")
        col3.metric("Average Duration", f"{total_duration/total_recordings:.1f}s")
        
        # Distribution by type
        types = [r['metadata']['type'] for r in st.session_state.audio_lab_recordings]
        type_counts = pd.Series(types).value_counts()
        
        fig_pie = px.pie(
            values=type_counts.values,
            names=type_counts.index,
            title="Recording Types Distribution"
        )
        st.plotly_chart(fig_pie, use_container_width=True)
        
        # Speakers distribution
        speakers = [r['metadata']['speaker'] for r in st.session_state.audio_lab_recordings]
        speaker_counts = pd.Series(speakers).value_counts()
        
        st.markdown("#### 👥 Speakers Distribution")
        st.bar_chart(speaker_counts)

# Global audio lab instance
audio_lab = AudioTrainingLab()
