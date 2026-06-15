import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import ListItemAvatar from "@mui/material/ListItemAvatar";
import Avatar from "@mui/material/Avatar";
import Typography from "@mui/material/Typography";

const REPOSITORY_URL = "https://github.com/troverld/auto-sekai-retriever";

export default function Info({ open, handleClose, config }) {
  return (
    <div>
      <Dialog
        open={open}
        onClose={handleClose}
        aria-labelledby="alert-dialog-title"
        aria-describedby="alert-dialog-description"
      >
        <DialogTitle id="alert-dialog-title">说明</DialogTitle>
        <DialogContent>
          <DialogContentText id="alert-dialog-description">
            <Typography variant="h6" component="h3">
              本工具得以实现，感谢：
            </Typography>
            <List>
              <ListItem
                button
                onClick={() =>
                  (window.location.href = "https://github.com/theoriginalayaka")
                }
              >
                <ListItemAvatar>
                  <Avatar
                    alt="Ayaka"
                    src="https://avatars.githubusercontent.com/theoriginalayaka"
                  />
                </ListItemAvatar>
                <ListItemText
                  primary="Ayaka"
                  secondary="原始创意来源"
                />
              </ListItem>
              <ListItem
                button
                onClick={() =>
                  (window.location.href = "https://github.com/modder4869")
                }
              >
                <ListItemAvatar>
                  <Avatar
                    alt="Modder4869"
                    src="https://avatars.githubusercontent.com/modder4869"
                  />
                </ListItemAvatar>
                <ListItemText
                  primary="Modder4869"
                  secondary="代码方面的帮助"
                />
              </ListItem>
              <ListItem
                button
                onClick={() =>
                  (window.location.href =
                    "https://www.reddit.com/r/ProjectSekai/comments/x1h4v1/after_an_ungodly_amount_of_time_i_finally_made/")
                }
              >
                <ListItemAvatar>
                  <Avatar
                    alt="u/SherenPlaysGames"
                    src="https://styles.redditmedia.com/t5_mygft/styles/profileIcon_n1kman41j5891.jpg"
                  />
                </ListItemAvatar>
                <ListItemText
                  primary="u/SherenPlaysGames"
                  secondary="原始表情素材来源"
                />
              </ListItem>
              <ListItem
                button
                onClick={() =>
                  (window.location.href =
                    `${REPOSITORY_URL}/graphs/contributors`)
                }
              >
                <ListItemAvatar>
                  <Avatar
                    alt="Contributors"
                    src="https://avatars.githubusercontent.com/u/583231"
                  />
                </ListItemAvatar>
                <ListItemText
                  primary="Contributors"
                  secondary="代码方面的帮助"
                />
              </ListItem>
            </List>
            <Typography variant="h6" component="h3">
              源代码与贡献入口：
            </Typography>
            <List>
              <ListItem
                button
                onClick={() =>
                  (window.location.href = REPOSITORY_URL)
                }
              >
                <ListItemAvatar>
                  <Avatar
                    alt="GitHub"
                    src="https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png"
                  />
                </ListItemAvatar>
                <ListItemText primary="GitHub" secondary="源代码" />
              </ListItem>
            </List>
            <Typography variant="h6" component="h3">
              使用本应用生成的表情总数：
              <br />
              {config?.global
                ? `${config.global.toLocaleString()} 张`
                : "暂无数据"}
            </Typography>
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClose} color="secondary" autoFocus>
            关闭
          </Button>
        </DialogActions>
      </Dialog>
    </div>
  );
}
