/** @jsx React.DOM */
var InstructionTable = React.createClass({
  getInitialState: function() {
    return {
      'kindleboxCsrfToken': this.props.kindleboxCsrfToken,
      'appUrl': this.props.appUrl,
      'active': this.props.active,
      'emailer': this.props.emailer,
    }
  },
  render: function() {
    if (this.state.active) {
      return <ActiveMessage deactivateHandler={this.deactivateHandler} />;
    }

    var instructionClasses = React.addons.classSet({
      'instruction-row': true,
      'instruction-completed': this.props.loggedIn,
    });
    var loginBtnClasses = React.addons.classSet({
      'instruction': true,
      'dropbox-action': true,
      'instruction-action': true,
      'instruction-action-inactive': this.props.loggedIn,
    });
    var loginInstruction = (
      <div className={instructionClasses}>
        <div className="instruction-num">
          1.
        </div>
        <a className="instruction-btn"
              href={ this.props.loginUrl }>
          <div className={ loginBtnClasses }>
            <div className="instruction-action-content">
              <img className="dropbox-logo" src="static/img/dropbox.png"/>
                Login with Dropbox
            </div>
          </div>
        </a>
      </div>
      );

    var emailerInstructions;
    if (this.props.loggedIn) {
      emailerInstructions = <EmailerInstructions
          kindleboxCsrfToken={this.state.kindleboxCsrfToken}
          appUrl={this.state.appUrl}
          emailer={this.state.emailer}
          deactivateHandler={this.deactivateHandler} />;
    }

    return (
      <div>
        {loginInstruction}
        {emailerInstructions}
      </div>
      );
  },
  deactivateHandler: function() {
    $.post('/deactivate', function(res) {
      if (res.success) {
        this.setState({
          'active': false,
        });
      }
    }.bind(this));
  }
});

var EmailerInstructions = React.createClass({
  render: function() {

    var bookmarklet = "javascript: (function() {" +
        "function addScript(source, callback) {" +
        "  var script = document.createElement(\"script\");" +
        "  script.type = \"text/javascript\";" +
        "  script.src = source;" +
        "  script.onload = callback;" +
        "  document.getElementsByTagName(\"head\")[0].appendChild(script);" +
        "}" +
        "function addScripts(scripts, callback) {" +
        "  if (scripts.length == 1) {" +
        "    addScript(scripts[0], callback);" +
        "  } else {" +
        "    addScript(scripts[0], function() {" +
        "      addScripts(scripts.slice(1), callback);" +
        "    });" +
        "  }" +
        "}" +
        "function addCSS(source) {" +
        "  var cssLink = document.createElement(\"link\");" +
        "  cssLink.href = source;" +
        "  cssLink.type = \"text/css\";" +
        "  cssLink.rel = \"stylesheet\";" +
        "  document.getElementsByTagName(\"head\")[0].appendChild(cssLink);" +
        "}" +
        "addCSS(\"https://kindlebox.me/static/css/lib/bootstrap.min.css\");" +
        "addScripts([" +
        "  \"https://kindlebox.me/static/js/lib/jquery-1.11.1.min.js\"," +
        "  \"https://kindlebox.me/static/js/lib/bootstrap.min.js\"," +
        "  \"https://kindlebox.me/static/js/bookmarklet.js\"" +
        "], function() {" +
        "    setDevice(1);" +
        "    setTimeout(function() {" +
        "      addModal(\"<kindleboxCsrfToken>\", \"<appUrl>\", \"<emailer>\");" +
        "      showModal();" +
        "    }, 0);" +
        "  });" +
        "}())";

    var start = bookmarklet.search('<.*>');
    var stop;
    var key;
    while (start > -1) {
      stop = bookmarklet.substring(start).search('>');
      key = bookmarklet.substring(start + 1, start + stop);
      bookmarklet = bookmarklet.replace('<' + key + '>', this.props[key]);
      start = bookmarklet.search('<.*>');
    }

    var lastInstructionDisplay = {
      'display': 'none',
    };

    return (
      <div>
        <div className="instruction-row">
          <div className="instruction-num">
            2.
          </div>
          <div className="instruction instruction-text">

            Drag this bookmarklet to your bookmarks bar:
            <div id="bookmarklet-wrapper" onDragEnd={this.showInstruction}>
              <a id="bookmarklet" className="instruction-action" href={bookmarklet}>Allow Kindlebox</a>
            </div>

          </div>
        </div>
        <div className="instruction-row" style={lastInstructionDisplay} ref="lastInstruction">
          <div className="instruction-num">
            3.
          </div>
          <div className="instruction instruction-text">

            Next, visit <a href="https://www.amazon.com/manageyourkindle"
            target="_blank">Manage Your Content and Devices</a>. Click the
            bookmarklet on your bookmarks bar from step 3, and you're good to
            go!

          </div>
        </div>
      </div>
    );
  },
  showInstruction: function() {
    var lastInstruction = this.refs.lastInstruction.getDOMNode();
    setTimeout(function() {
      $(lastInstruction).fadeIn();
    }, 500);
  },
});

var ActiveMessage = React.createClass({
  render: function() {
    return (
        <div>
          <div>
            <h2>
              Success! Any books you add to <code>Dropbox/Apps/kindle-box</code> will now be
              sent to your Kindle.
            </h2>
          </div>
          <div id="stop">
            If you'd like to change your Kindle username, or
            stop using Kindlebox completely, <a
            onClick={this.deactivateHandler}
            className="instruction-btn">click here</a>.
          </div>
        </div>
      );
  },
  deactivateHandler: function() {
    this.props.deactivateHandler();
  },
});
