from jinja2 import Environment, FileSystemLoader
import os

root = os.path.dirname(os.path.abspath(__file__))
templates_dir = os.path.join(root, 'templates')
env = Environment(loader=FileSystemLoader(templates_dir))
template = env.get_template('script-turns.html.j2')

script = ['What time of day would you like the TV to turn off automatically?', 'Which day or days of the week would you like the TV to turn on automatically?', 'What volume number (between 1 and 100) would you like the TV to be at?', 'How about the brightness level (between 1 and 100)?', 'Can you tell me the channel would you like the TV to be on?']

filename = os.path.join(root, 'html', 'index.html')
with open(filename, 'w') as fh:
    fh.write(template.render(
        script=script
    ))


'''

 <div class="row">
      <div class="column">
        <ul id="sortable" style="list-style-type:none;">
          {% for turn in script %}
          <li class="counter">
            <span>&#x21C5;</span><input type="text" class="counter" value="{{ loop.counter }}"/>
          </li>
          {% endfor %}
        </ul>
      </div>
      <div class="column">
        <ul id="sortable-prompts" style="list-style-type:none;">
          {% for turn in script %}
          <li class="ui-state-default">
            <input type="text" class="prompt" value="{{ turn }}"/>
          </li>
          {% endfor %}
        </ul>
      </div>
    </div>
'''