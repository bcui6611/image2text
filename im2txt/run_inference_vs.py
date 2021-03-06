# Copyright 2016 The TensorFlow Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
r"""Generate captions for images using default beam search parameters."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import math
import os


import tensorflow as tf

from im2txt import configuration
from im2txt import inference_wrapper
from im2txt.inference_utils import caption_generator
from im2txt.inference_utils import vocabulary

# Mysql
import pymysql
import pymysql.cursors
from PIL import Image
import PIL.Image
from io import BytesIO
import requests

db = pymysql.connect(user='nao', password='control1234', host='mydbinst-rds.catb3i4xromj.us-west-2.rds.amazonaws.com', database='nao_db', cursorclass=pymysql.cursors.DictCursor)
db.autocommit(True)
cur=db.cursor()


FLAGS = tf.flags.FLAGS

tf.flags.DEFINE_string("checkpoint_path", "/home/sorelys/im2txt/model/train/model.ckpt-3000000",
                       "Model checkpoint file or directory containing a "
                       "model checkpoint file.")
tf.flags.DEFINE_string("vocab_file", "/home/sorelys/im2txt/data/mscoco/word_counts3.txt", "Text file containing the vocabulary.")
tf.flags.DEFINE_string("input_files", "",
                       "File pattern or comma-separated list of file patterns "
                       "of image files.")

tf.logging.set_verbosity(tf.logging.INFO)


def main(_):
  # Build the inference graph.
  g = tf.Graph()
  with g.as_default():
    model = inference_wrapper.InferenceWrapper()
    restore_fn = model.build_graph_from_config(configuration.ModelConfig(),
                                               FLAGS.checkpoint_path)
  g.finalize()

  # Create the vocabulary.
  vocab = vocabulary.Vocabulary(FLAGS.vocab_file)

  """ 
  filenames = []
  for file_pattern in FLAGS.input_files.split(","):
    filenames.extend(tf.gfile.Glob(file_pattern))
  tf.logging.info("Running caption generation on %d files matching %s",
                  len(filenames), FLAGS.input_files)
  """
  with tf.Session(graph=g) as sess:
    # Load the model from checkpoint.
    restore_fn(sess)

    # Prepare the caption generator. Here we are implicitly using the default
    # beam search parameters. See caption_generator.py for a description of the
    # available beam search parameters.
    generator = caption_generator.CaptionGenerator(model, vocab)
    
    cur.execute("SELECT DISTINCT image_id,image_url FROM annotations")
    urls = cur.fetchall()
    for url in urls: #for array con urls
      try:
        response = requests.get(url['image_url'])
        file_like = BytesIO(response.content)
        image = file_like.getvalue()
        
        #img=PIL.Image.open(file_like)
        #image = tf.image.decode_jpeg(str(list(img.getdata())));

        captions = generator.beam_search(sess, image)
        #print("Captions for image %s:" % os.path.basename(filename))
        caption = captions[0]
        #for i, caption in enumerate(captions):
          # Ignore begin and end words.
        sentence = [vocab.id_to_word(w) for w in caption.sentence[1:-1]]
        sentence = " ".join(sentence)
          #print("  %d) %s (p=%f)" % (i, sentence, math.exp(caption.logprob)))
          #cur.execute("INSERT INTO img2txt(id_image,caption,caption_p) VALUES (%s,%s,%s)",(old_id,sentence,math.exp(caption.logprob)))
          #db.commit();
        query = ("UPDATE annotations SET image_caption=%s WHERE image_id=%s")
        cur.execute(query,(sentence,url['image_id']))
        print(sentence)
      except KeyboardInterrupt:
        db.close();
        break



if __name__ == "__main__":
  tf.app.run()